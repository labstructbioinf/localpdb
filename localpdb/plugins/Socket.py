import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
import tempfile
import shutil
import re
import pandas as pd
from localpdb.utils.os import create_directory, multiprocess, os_cmd, get_unzipped_tempfile


class Socket(Plugin):

    ### Beginning of the part required for proper plugin handling ###
    #################################################################
    plugin_name = os.path.basename(__file__).split('.')[0] # Name of the plugin based on the filename
    plugin_config = Config(
        f'{os.path.dirname(os.path.realpath(__file__))}/config/{plugin_name}.yml').data  # Plugin config (dict)
    plugin_dir = plugin_config['path']
    ###########################################################
    ### End of the part required for proper plugin handling ###

    def __init__(self, lpdb):
        super().__init__(lpdb)
        self.fn_template = ["{{ plugin_dir }}/{{ pdb_id[1:3]}}/{{ pdb_id }}_socket_7.0",
                            "{{ plugin_dir }}/{{ pdb_id[1:3]}}/{{ pdb_id }}_socket_7.2",
                            "{{ plugin_dir }}/{{ pdb_id[1:3]}}/{{ pdb_id }}_socket_7.4"]
        self.socket_cutoffs = ['7.0', '7.2', '7.4']

    def _load(self):
        data_dict = {'socket_{}'.format(cutoff): {} for cutoff in self.socket_cutoffs}  # Data store for all cutoffs
        for key, pdb_id in self.id_dict.items():
            for cutoff in self.socket_cutoffs:
                fn_out = f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}_socket_{cutoff}'
                if os.path.isfile(fn_out):
                    data_dict['socket_{}'.format(cutoff)][key] = fn_out
        self.lpdb._add_col_structures(pd.DataFrame.from_dict(data_dict))
        self.lpdb.get_socket_dict = self.get_socket_dict.__get__(self)

    def _setup(self):
        self.lpdb.load_plugin('Biounit')
        self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['biounit'].notnull()]
        cmds = {pdb_id: (pdb_id, fn_biounit, self.socket_cutoffs, f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}_socket',
                         self.plugin_config['socket_loc'], self.plugin_config['dssp2_loc']) for pdb_id, fn_biounit in
                self.lpdb.entries['biounit'].to_dict().items()}
        # Run socket for all entries
        status = multiprocess(run_socket, cmds, return_type='failed', process_executor=True)
        out_log = {'no_entries': len(cmds), 'no_failed_entries': len(status), 'failed_entries_ids': list(status)}
        return out_log

    def _prep_paths(self):
        pdb_ids = set(pdb_id[1:3] for pdb_id in self.lpdb.entries.index.tolist())
        create_directory(self.plugin_dir)
        for pdb_id in pdb_ids:
            create_directory(f'{self.plugin_dir}/{pdb_id}')

    def get_socket_dict(self,  cutoff='7.4', method='overlap'):
        sp = SocketParser(method=method)
        if cutoff not in self.socket_cutoffs:
            raise ValueError(f'Data for socket runs at cutoff \'{cutoff}\' was not loaded and/or calculated!')
        socket_dict = {pdb_id: sp.parse(f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}_socket_{cutoff}') for pdb_id in
                       self.lpdb.entries[self.lpdb.entries[f'socket_{cutoff}'].notnull()].index}
        return socket_dict


def run_socket(inps):
    """
    Runs socket (preceeded by the DSSP run) and writes the output in the plugin directory. Output is written only if
    coiled coil domain was found in the entry. Inputs are wrapped to allow for multiprocessing.
    Order of the inputs is: pdb_id: PDB identifier, fn_biounit: filename of the biounit, cutoffs: socket cutoffs to run,
    fn_out: filename of the output file if there's any., socket_loc: location of the socket binary, dssp2_loc: location
    of the dssp2 binary.
    :param inps: tuple containing (pdb_id, fn_biounit, cutoffs, fn_out, socket_loc, dssp2_loc)
    :return: dict with the job statuses (NaN or pointer to output file) with socket cutoffs as keys
    """
    pdb_id, fn_biounit, cutoffs, fn_out, socket_loc, dssp2_loc = inps
    fh_tmp = get_unzipped_tempfile(fn_biounit) # Unzipped fh to the biounit file
    dssp_tmp = '/tmp/{}'.format(next(tempfile._get_candidate_names()))
    cmd = f'{dssp2_loc} -i {fn_biounit} -o {dssp_tmp}'
    result, _ = os_cmd(cmd)
    codes = [result]
    if os.path.isfile(dssp_tmp) and result == 0: # DSSP run was OK, proceed with socket
        for cutoff in cutoffs: # Run socket for each cutoff and check if CC was found
            socket_tmp = '/tmp/{}'.format(next(tempfile._get_candidate_names()))
            cmd = f'{socket_loc} -f {fh_tmp.name} -s {dssp_tmp} -c {cutoff}'
            code, (stdout, stderr) = os_cmd(cmd)
            has_cc = any(['COILED COILS PRESENT' in line for line in stdout])
            if has_cc and code == 0:
                full_fn_out = f'{fn_out}_{cutoff}'
                fs = open(full_fn_out, 'w')
                for line in stdout:
                    fs.write(f'{line}\n')
                fs.close()
            codes.append(code)
        os.remove(dssp_tmp) # Remove tmp file
    fh_tmp.close() # Close unzipped biounit fh and delete file
    if codes.count(0) == len(codes):
        return 0, None
    else:
        return 1, None


class SocketParser:

    def __init__(self, method='overlap'):
        """
        Parser of the Socket (J. Mol. Biol., 307 (5), 1427-1450) coiled coil structural detection algorithm
        :param method: Assignment method
                    'heptads' - based on the heptad assignment
                    'knobs' - based on the knobs assignment
                    'overlap' - sum of the ranges of 'heptads' and 'knobs'
        """
        if method not in ['heptads', 'knobs', 'overlap']:
            raise ValueError(
                'Detection method \'{}\' is not valid. Choose from either \'heptads\', \'knobs\' or \'overlap\'.'.format(
                    method))
        self.method = method

    def parse(self, filename):
        try:
            f = open(filename, 'r')
            lines = [line.rstrip('\n') for line in f.readlines()]
            f.close()
        except (OSError, FileNotFoundError):
            raise ValueError('Input file is not valid Socket output')

        # Get indices (numbers of first line in file) for each CC assignment
        cc_line_indices = [i for i in range(0, len(lines))
                           if (lines[i].startswith('coiled coil') and lines[i].endswith(':')) or 'Finished' in lines[i]]
        cc_all_text_data = [lines[cc_line_indices[i]:cc_line_indices[i + 1]] for i in
                            range(0, len(cc_line_indices) - 1)]
        # Iterate over each CC description
        coil_info = {}
        for cc_text_data in cc_all_text_data:
            cc_id = 'cc_{}'.format(cc_text_data[0].split()[2].replace(':', ''))
            coil_info.update({cc_id: self.parse_cc_data(cc_text_data)})
        return coil_info

    @staticmethod
    def get_res_range(res_range):
        """
        Helper function to parse residue range from the Socket output file.
        In some cases coiled coil residue range may span the negative residues which is not handled well in original
        Socket output file e.g.:
        Normal res_range: '472-490:A'
        'Weird' res_range '-5-12:A'
        :param res_range: residue range parsed from Socket output
        :return: beg_res, end_res - start and end indexes of CC domain
        """
        if res_range[0] == '-':  # First residue is negative
            # Both residues are negative (no need to handle only end residue being negative)
            if res_range.count('-') == 3:
                beg_res = -int(res_range.split('-')[1])
                end_res = -int(res_range.split('-')[3].split(':')[0])
            else:
                beg_res = -int(res_range.split('-')[1])
                end_res = int(res_range.split('-')[2].split(':')[0])
        # Only positive residues
        else:
            beg_res = int(res_range.split('-')[0])
            end_res = int(res_range.split('-')[1].split(':')[0])
        return beg_res, end_res

    def parse_cc_data(self, cc_text_data):
        cc_data = {'helix_ids': [], 'indices': {}, 'sequences': {}, 'heptads': {}, 'ambigous': False, 'relations': []}
        for i, line in enumerate(cc_text_data):
            if line.startswith('assigning heptad to helix'):
                temp = line.split(' ')
                res_range = temp[6]

                beg_res, end_res = self.get_res_range(res_range)
                helix_id = 'helix_{}'.format(int(temp[4]))
                cc_data['helix_ids'].append(helix_id)
                chain = line.split(':')[1]
                seq = cc_text_data[i + 2][9:]
                register = cc_text_data[i + 3][9:]
                knobtype = cc_text_data[i + 5][9:]

                if len(seq) != (end_res - beg_res + 1):
                    cc_data['ambigous'] = True

                knob_matches = [match.start() for match in re.finditer('[0-9]', knobtype)]
                knob_beg = knob_matches[0]
                knob_end = knob_matches[-1] + 1

                reg_matches = [match.start() for match in re.finditer('\w', register)]
                try: # Handle a case where there's no register assignment at all (e.g. 4xyd)
                    reg_beg = reg_matches[0]
                    reg_end = reg_matches[-1] + 1
                except IndexError:
                    reg_beg = knob_beg
                    reg_end = knob_end

                if self.method == 'overlap':
                    beg = min(reg_beg, knob_beg)
                    end = max(reg_end, knob_end)
                elif self.method == 'heptads':
                    beg = reg_beg
                    end = reg_end
                elif self.method == 'knobs':
                    beg = knob_beg
                    end = knob_end

                end_res = end_res - (len(seq) - end)
                beg_res += beg
                seq = seq[beg:end]
                register = register[beg:end].replace(' ', '-')
                assert len(seq) == len(register)
                cc_data['heptads'][helix_id] = register
                cc_data['sequences'][helix_id] = seq
                cc_data['indices'][helix_id] = {'start': int(beg_res), 'end': int(end_res), 'chain': chain}

            if 'length max' in line and 'PRESENT' not in line and 'REPEATS' not in line:
                inf = re.findall('\((.*?)\)', line)
                data = inf[1].split(' ')
                oligomerization = int(data[1][0])
                orientation = data[0]
                cc_data['oligomerization'] = oligomerization
                cc_data['orientation'] = orientation

            if line.startswith('\tangle between helices'):
                rel_data = line.split()
                first_helix, second_helix = 'helix_{}'.format(rel_data[3]), 'helix_{}'.format(rel_data[5])
                orientation = rel_data[8]
                cc_data['relations'].append((first_helix, second_helix, orientation))

        return cc_data