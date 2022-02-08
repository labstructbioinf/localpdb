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
from localpdb.utils.os import multiprocess, os_cmd, get_unzipped_tempfile
from Bio.PDB import Select
from Bio.PDB.PDBParser import PDBParser
from Bio.PDB import PDBIO


class MasterChain(Plugin):

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
        self.fn_template = ["{{ plugin_dir }}/{{ pdb_id[1:3] }}/{{ pdb_id }}_{{ chain }}.pds"]
        self.master_loc = self.plugin_config['master_loc']

    def _load(self):
        fn_dict = {pdb_chain: f'{self.plugin_dir}/{pdb_chain[1:3]}/{self.id_dict[pdb_chain[0:4]]}_{pdb_chain[5:]}.pds' for
                   pdb_chain in self.lpdb.chains.index if os.path.isfile(
                f'{self.plugin_dir}/{pdb_chain[1:3]}/{self.id_dict[pdb_chain[0:4]]}_{pdb_chain[5:]}.pds')}
        self.lpdb._add_col_chains(fn_dict, ['master'])

    def _setup(self):
        self.lpdb.load_plugin('PDBChain')
        self.lpdb.chains = self.lpdb.chains[self.lpdb.chains['pdb_fn'].notnull()]
        cmds = {}
        for pdb_chain in self.lpdb.chains.index:
            in_fn = f'{self.lpdb.db_path}/pdb_chain/{pdb_chain[1:3]}/{pdb_chain}.pdb.gz'
            out_fn = f'{self.plugin_dir}/{pdb_chain[1:3]}/{pdb_chain}.pds'
            chain = pdb_chain[5:]
            cmds[pdb_chain] = (in_fn, out_fn, self.master_loc)
        status = multiprocess(run_master, cmds, return_type='failed', process_executor=True)
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


def run_master(inps):
    fn_pdb_chain, fn_out, master_loc = inps
    fh_tmp = get_unzipped_tempfile(fn_pdb_chain)  # Unzipped fh to the biounit file
    cmd = 'timeout 60s {} --pdb {} --pds {} --type target --cleanPDB'.format(master_loc, fh_tmp.name, fn_out)
    status = os_cmd(cmd)
    fh_tmp.close()  # Close unzipped biounit fh and delete file
    return status, None
