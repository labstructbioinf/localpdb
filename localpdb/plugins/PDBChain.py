import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
import gzip
import shutil
from localpdb.utils.os import multiprocess, os_cmd
from Bio.PDB import Select
from Bio.PDB.PDBParser import PDBParser
from Bio.PDB import PDBIO


class PDBChain(Plugin):

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
        self.fn_template = ["{{ plugin_dir }}/{{ pdb_id[1:3] }}/{{ pdb_id }}_{{ chain }}.pdb.gz"]
        self.script_loc = os.path.dirname(os.path.abspath(__file__)) + '/utils/PDBExtractChain.py'

    def _load(self):
        fn_dict = {pdb_chain: f'{self.plugin_dir}/{pdb_chain[1:3]}/{self.id_dict[pdb_chain[0:4]]}_{pdb_chain[5:]}.pdb.gz' for
                   pdb_chain in self.lpdb.chains.index if os.path.isfile(
                f'{self.plugin_dir}/{pdb_chain[1:3]}/{self.id_dict[pdb_chain[0:4]]}_{pdb_chain[5:]}.pdb.gz')}
        self.lpdb._add_col_chains(fn_dict, ['pdb_fn'])

    def _setup(self):
        cmds = {}
        for pdb_chain in self.lpdb.chains.index:
            in_fn = f'{self.lpdb.db_path}/mirror/pdb/{pdb_chain[1:3]}/pdb{pdb_chain[0:4]}.ent.gz'
            out_fn = f'{self.plugin_dir}/{pdb_chain[1:3]}/{pdb_chain}.pdb'
            chain = pdb_chain[5:]
            #cmd = f'timeout 10s python {self.script_loc} -i {in_fn} -o {out_fn} -chain {pdb_chain[5:]}'
            cmds[pdb_chain] = (in_fn, chain, out_fn)
        status = multiprocess(extract_chain, cmds, return_type='failed', process_executor=True)
        out_log = {'no_entries': len(cmds), 'no_failed_entries': len(status), 'failed_entries_ids': list(status)}
        return out_log

    def _adjust_fns(self):
        _, map_dict = self.lpdb._pdbv.adjust_pdb_ids({id_: id_ for id_ in self.lpdb.entries.index},
                                                     self.lpdb.version, mode='setup')

        for pdb_chain in self.lpdb.chains[self.lpdb.chains['pdb'].isin(set(map_dict.keys()))].index:

            pdb_id, chain = pdb_chain.split('_')

            param_dict = locals()
            param_dict.update(self.__dict__)
            org_fns = self._render_template(param_dict)

            pdb_id = map_dict[pdb_id]
            param_dict = locals()
            param_dict.update(self.__dict__)

            dest_fns = self._render_template(param_dict)

            for org_fn, dest_fn in zip(org_fns, dest_fns):
                try:
                    shutil.copy2(org_fn, dest_fn)
                    self.cp_files.append((org_fn, dest_fn))
                    logger.debug(f'Moved file\'{org_fn}\' to \'{dest_fn}\'.')
                except:
                    logger.debug(f'File \'{org_fn}\' that was supposed to be moved (versioning) does not exist.')
    def _prep_paths(self):
        pdb_ids = set(pdb_id[1:3] for pdb_id in self.lpdb.entries.index)
        create_directory(self.plugin_dir)
        for pdb_id in pdb_ids:
            create_directory(f'{self.plugin_dir}/{pdb_id}')

class SelectChains(Select):
    """ Only accept the specified chains when saving. """

    def __init__(self, chain_letters):
        self.chain_letters = chain_letters

    def accept_atom(self, atom):
        if (not atom.is_disordered()) or atom.get_altloc() == 'A' or atom.get_altloc() == '1':
            atom.set_altloc(' ')  # Eliminate alt location ID before output.
            return True
        else:  # Alt location was not one to be output.
            return False

    def accept_chain(self, chain):
        return chain.get_id() in self.chain_letters

def extract_chain(args):
    in_fn, chain, out_fn = args
    parser = PDBParser(QUIET=True)
    writer = PDBIO()
    with gzip.open(in_fn, 'rt') as f:
        struct = parser.get_structure('A', f)
    writer.set_structure(struct)
    writer.save(out_fn, select=SelectChains(chain))
    result = os.system(f'gzip -f {out_fn}')
    return result, None