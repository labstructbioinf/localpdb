import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports


class PDBClustering(Plugin):

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

    def _load(self):
        self.lpdb.load_clustering_data = self.load_clustering_data.__get__(self)

    def _prep_paths(self):
        create_directory(f'{self.plugin_dir}/')
        create_directory(f'{self.plugin_dir}/{self.plugin_version}')

    def _setup(self):
        clust_redundancy = [30, 40, 50, 70, 90, 95, 100]
        for redundancy in clust_redundancy:
            local_fn = f'{self.plugin_dir}/{self.plugin_version}/bc-{redundancy}.out'
            url = self.plugin_config['clust_url'] + f'bc-{redundancy}.out'
            download_url(url, local_fn)

    def _reset(self):
        del self.lpdb.ecod
        self._load()

    def load_clustering_data(self, redundancy=50):
        valid_cutoffs = ['30', '40', '50', '70', '90', '95', '100']
        if not str(redundancy) in valid_cutoffs:
            cutoffs = ', '.join(valid_cutoffs)
            raise ValueError(f'Cutoff \'{redundancy}\' is not a valid PDB clustering cutoff! Use any of the following: {cutoffs}')
        fn = f'{self.plugin_dir}/{self.plugin_version}/bc-{redundancy}.out'
        _, pdb_idxs = self.lpdb._get_current_indexes()
        cluster_data_filt = {key: value for key, value in parse_cluster_data(fn).items() if key in pdb_idxs}
        self.lpdb._add_col_chains(cluster_data_filt, [f'clust-{redundancy}'])

def parse_cluster_data(fn):
    """
    Parse PDB protein sequences clustering data available from the RCSB website
    @param fn: filename with clustering data
    @return: dictionary with pdb_chain as keys and cluster number (integer)
    """
    f = open(fn, 'r')
    data = [line.rstrip() for line in f.readlines()]
    f.close()
    cluster_data = {}
    for c in range(1, len(data)+1):
        for entry in data[c-1].split(' '):
            pdb, chain = entry.split('_')
            cluster_data['{}_{}'.format(pdb.lower(), chain)] = str(c)
    return cluster_data
