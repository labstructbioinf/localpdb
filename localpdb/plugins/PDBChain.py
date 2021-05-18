import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
from localpdb.utils.os import multiprocess, os_cmd


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
        self.script_loc = os.path.dirname(os.path.abspath(__file__)) + '/utils/PDBExtractChain.py'

    def _load(self):
        data_dict = {pdb_chain: f'{self.plugin_dir}/{pdb_chain[1:3]}/{pdb_chain}.pdb.gz' for pdb_chain in
                     self.lpdb.chains.index if os.path.isfile(f'{self.plugin_dir}/{pdb_chain[1:3]}/{pdb_chain}.pdb.gz')}
        self.lpdb._add_col_chains(data_dict, ['pdb_fn'])

    def _setup(self):
        self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['pdb_fn'].notnull()]
        cmds = {}
        for pdb_chain in self.lpdb.chains.index.tolist():
            in_fn = f'{self.lpdb.db_path}/mirror/pdb/{pdb_chain[1:3]}/pdb{pdb_chain[0:4]}.ent.gz'
            out_fn = f'{self.plugin_dir}/{pdb_chain[1:3]}/{pdb_chain}.pdb'
            cmd = f'timeout 10s python {self.script_loc} -i {in_fn} -o {out_fn} -chain {pdb_chain[5:]}'
            cmds[pdb_chain] = cmd
        status = multiprocess(os_cmd, cmds, return_type='failed')
        out_log = {'no_entries': len(cmds), 'no_failed_entries': len(status), 'failed_entries_ids': list(status)}
        return out_log

    def _prep_paths(self):
        pdb_ids = set(pdb_id[1:3] for pdb_id in self.lpdb.entries.index.tolist())
        create_directory(self.plugin_dir)
        for pdb_id in pdb_ids:
            create_directory(f'{self.plugin_dir}/{pdb_id}')