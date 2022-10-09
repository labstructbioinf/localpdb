import logging
import os
import requests
import json
import numpy as np
from tqdm import tqdm
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
            url = self.plugin_config['clust_url'] + f'clusters-by-entity-{redundancy}.txt'
            download_url(url, local_fn)

        entity_instance_mapping = {}
        local_fn = f'{self.plugin_dir}/{self.plugin_version}/mapping.json'
        entries = [idx.upper() for idx in self.lpdb.entries.index]
        for batch in tqdm(np.array_split(entries, 250)):
            entity_instance_mapping.update(fetch_entity_instance_mapping(batch))
        with open(local_fn, 'w') as f:
            f.write(json.dumps(entity_instance_mapping, indent=4))

    def _reset(self):
        self._load()

    def load_clustering_data(self, redundancy=50):
        valid_cutoffs = ['30', '40', '50', '70', '90', '95', '100']
        if not str(redundancy) in valid_cutoffs:
            cutoffs = ', '.join(valid_cutoffs)
            raise ValueError(f'Cutoff \'{redundancy}\' is not a valid PDB clustering cutoff! Use any of the following: {cutoffs}')
        fn_mapping = f'{self.plugin_dir}/{self.plugin_version}/mapping.json'
        fn = f'{self.plugin_dir}/{self.plugin_version}/bc-{redundancy}.out'
        _, pdb_idxs = self.lpdb._get_current_indexes()
        if os.path.isfile(fn_mapping):
            initial_clusters = parse_cluster_data(fn)
            with open(fn_mapping) as f:
                mapping = json.loads(f.read())
                mapping_corr = {key: value.lower() for key, value in mapping.items()}
            cluster_data_filt = {key: initial_clusters.get(mapping_corr.get(key, None), None) for key in pdb_idxs}
        else:
            cluster_data_filt = {key: value for key, value in parse_cluster_data(fn).items() if key in pdb_idxs}
        self.lpdb._add_col_chains(cluster_data_filt, [f'clust-{redundancy}'])


def fetch_entity_instance_mapping(entries):
    query = """{entries(entry_ids: %s) {polymer_entities {rcsb_id, rcsb_polymer_entity_container_identifiers {auth_asym_ids}}}}""" % json.dumps(
        list(entries))
    res = requests.post("https://data.rcsb.org/graphql", json={"query": query}).json()['data']['entries']
    data = {'{}_{}'.format(ent['rcsb_id'].split('_')[0].lower(), chain): ent['rcsb_id'] 
        for r in res for ent in r['polymer_entities'] 
        for chain in ent['rcsb_polymer_entity_container_identifiers']['auth_asym_ids']}
    return data


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
            if len(entry.split('_')) == 2:
                pdb, chain = entry.split('_')
                cluster_data['{}_{}'.format(pdb.lower(), chain)] = str(c)
    return cluster_data
