import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
from localpdb.utils.os import multiprocess, os_cmd


class DSSP(Plugin):

    ### Beginning of the part required for proper plugin handling ###
    #################################################################
    plugin_name = os.path.basename(__file__).split('.')[0]  # Name of the plugin based on the filename
    plugin_config = Config(
        f'{os.path.dirname(os.path.realpath(__file__))}/config/{plugin_name}.yml').data  # Plugin config (dict)
    plugin_dir = plugin_config['path']

    ###########################################################
    ### End of the part required for proper plugin handling ###

    def __init__(self, lpdb):
        super().__init__(lpdb)
        self.fn_template = ["{{ plugin_dir }}/{{ pdb_id[1:3] }}/{{ pdb_id }}.dssp.gz"]
        self.dssp_loc = self.plugin_config['dssp_loc']

    def _load(self):
        fn_dict = {key: f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}.dssp.gz' for key, pdb_id in self.id_dict.items() if
                   os.path.isfile(f'{self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}.dssp.gz')}
        # Point to the original filenames for NMR and EM structures
        self.lpdb._add_col_structures(fn_dict, ['dssp'])

    def _setup(self):
        self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['mmCIF_fn'].notnull()]
        cmds = {pdb_id: f'{self.dssp_loc} -i {fn_struct} -o {self.plugin_dir}/{pdb_id[1:3]}/{pdb_id}.dssp.gz' for
                pdb_id, fn_struct in self.lpdb.entries['mmCIF_fn'].to_dict().items()}
        status = multiprocess(os_cmd, cmds, return_type='failed', process_executor=True)
        out_log = {'no_entries': len(cmds), 'no_failed_entries': len(status), 'failed_entries_ids': list(status)}
        return out_log

    def _prep_paths(self):
        pdb_ids = set(pdb_id[1:3] for pdb_id in self.lpdb.entries.index.tolist())
        create_directory(self.plugin_dir)
        for pdb_id in pdb_ids:
            create_directory(f'{self.plugin_dir}/{pdb_id}')
