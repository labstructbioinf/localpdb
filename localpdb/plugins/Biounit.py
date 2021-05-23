import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
from localpdb.utils.os import multiprocess, os_cmd



class Biounit(Plugin):

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
        self.fn_template = ["{{ plugin_dir }}/{{ pdb_id[1:3] }}/{{ pdb_id }}.pdb.gz"]
        self.script_loc = os.path.dirname(os.path.abspath(__file__)) + '/utils/MakeMultimer.py'

    def _load(self):
        # Point to calculated biounits for X-ray structures
        fn_dict = {key: f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}.pdb.gz' for key, pdb_id in self.id_dict.items() if
                   os.path.isfile(f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}.pdb.gz')}
        # Point to the original filenames for NMR and EM structures
        nonstd_dict = {pdb_id: fn_struct for pdb_id, fn_struct in
                       self.lpdb.entries[self.lpdb.entries['method'].isin(['NMR', 'EM'])]['pdb_fn'].to_dict().items()}
        fn_dict.update(nonstd_dict)
        self.lpdb._add_col_structures(fn_dict, ['biounit'])

    def _setup(self):
        self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['pdb_fn'].notnull()]
        cmds = {
            pdb_id: f'python {self.script_loc} -w -c 1 -i {fn_struct} -in_gz -out_gz -out_prefix {pdb_id} -first -out_path {self.plugin_dir}/{pdb_id[1:3]}/'
            for pdb_id, fn_struct in
            self.lpdb.entries[self.lpdb.entries['method'] == 'diffraction']['pdb_fn'].to_dict().items()}
        status = multiprocess(os_cmd, cmds, return_type='failed', process_executor=True)
        out_log = {'no_entries': len(cmds), 'no_failed_entries': len(status), 'failed_entries_ids': list(status)}
        return out_log

    def _prep_paths(self):
        pdb_ids = set(pdb_id[1:3] for pdb_id in self.lpdb.entries.index.tolist())
        create_directory(self.plugin_dir)
        for pdb_id in pdb_ids:
            create_directory(f'{self.plugin_dir}/{pdb_id}')
