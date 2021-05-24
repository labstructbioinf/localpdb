import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
import gzip
import pandas as pd
from urllib.parse import urlparse


class SIFTS(Plugin):

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

        self.taxonomy_fn = f'{self.plugin_dir}/{self.plugin_version}/pdb_chain_taxonomy.tsv.gz'
        self.ec_fn = f'{self.plugin_dir}/{self.plugin_version}/pdb_chain_enzyme.tsv.gz'
        self.pfam_fn = f'{self.plugin_dir}/{self.plugin_version}/pdb_chain_pfam.tsv.gz'
        self.cath_fn = f'{self.plugin_dir}/{self.plugin_version}/pdb_chain_cath_uniprot.tsv.gz'
        self.scop_fn = f'{self.plugin_dir}/{self.plugin_version}/pdb_chain_scop_uniprot.tsv.gz'

    def _load(self):
        self.__load_taxonomy()
        self.lpdb._register_attr('ec')
        self.__load_ec()
        self.lpdb._register_attr('pfam')
        self.__load_pfam()
        self.lpdb._register_attr('cath')
        self.__load_cath()
        self.lpdb._register_attr('scop')
        self.__load_scop()

    def __load_taxonomy(self):
        tmp_df = pd.read_csv(self.taxonomy_fn, skiprows=1, sep='\t')
        tmp_df['pdb_chain'] = tmp_df['PDB'] + '_' + tmp_df['CHAIN']
        tmp_df_wrapped = tmp_df.groupby(by='pdb_chain').agg({'TAX_ID': 'first'})
        tmp_df_wrapped.columns = ['ncbi_taxid']
        tmp_df_wrapped['ncbi_taxid'] = tmp_df_wrapped['ncbi_taxid'].astype(str)
        self.lpdb._add_col_chains(tmp_df_wrapped)

    def __load_ec(self):
        tmp_df = pd.read_csv(self.ec_fn, skiprows=1, sep='\t')
        tmp_df['pdb_chain'] = tmp_df['PDB'] + '_' + tmp_df['CHAIN']
        tmp_df = tmp_df[['pdb_chain', 'PDB', 'EC_NUMBER']]
        tmp_df.columns = ['pdb_chain', 'pdb', 'ec_id']
        _, pdb_chain_ids = self.lpdb._get_current_indexes()
        tmp_df = tmp_df[tmp_df['pdb_chain'].isin(pdb_chain_ids)]
        self.lpdb.ec = tmp_df

    def __load_pfam(self):
        tmp_df = pd.read_csv(self.pfam_fn, skiprows=1, sep='\t')
        tmp_df['pdb_chain'] = tmp_df['PDB'] + '_' + tmp_df['CHAIN']
        tmp_df = tmp_df[['PDB', 'pdb_chain', 'PFAM_ID', 'COVERAGE']]
        tmp_df.columns = ['pdb', 'pdb_chain', 'pfam_id', 'pfam_cov']
        _, pdb_chain_ids = self.lpdb._get_current_indexes()
        tmp_df = tmp_df[tmp_df['pdb_chain'].isin(pdb_chain_ids)]
        self.lpdb.pfam = tmp_df

    def __load_cath(self):
        tmp_df = pd.read_csv(self.cath_fn, skiprows=1, sep='\t')
        tmp_df['pdb_chain'] = tmp_df['PDB'] + '_' + tmp_df['CHAIN']
        tmp_df = tmp_df[['PDB', 'pdb_chain', 'CATH_ID']]
        tmp_df.columns = ['pdb', 'pdb_chain', 'cath_id']
        _, pdb_chain_ids = self.lpdb._get_current_indexes()
        tmp_df = tmp_df[tmp_df['pdb_chain'].isin(pdb_chain_ids)]
        self.lpdb.cath = tmp_df

    def __load_scop(self):
        tmp_df = pd.read_csv(self.scop_fn, skiprows=1, sep='\t')
        tmp_df['pdb_chain'] = tmp_df['PDB'] + '_' + tmp_df['CHAIN']
        tmp_df = tmp_df[['PDB', 'pdb_chain', 'SCOP_ID']]
        tmp_df.columns = ['pdb', 'pdb_chain', 'scop_id']
        _, pdb_chain_ids = self.lpdb._get_current_indexes()
        tmp_df = tmp_df[tmp_df['pdb_chain'].isin(pdb_chain_ids)]
        self.lpdb.scop = tmp_df

    def _prep_paths(self):
        create_directory(f'{self.plugin_dir}/')
        create_directory(f'{self.plugin_dir}/{self.plugin_version}')

    def _setup(self):

        out_dir = f'{self.plugin_dir}/{self.plugin_version}/'
        for name, url in self.plugin_config['urls'].items():
            out_fn = '{}/{}'.format(out_dir, os.path.basename(urlparse(url).path))
            download_url(url, out_fn, ftp=True)

    def _filter_chains(self, chains):
        self.lpdb.pfam = self.lpdb.pfam[self.lpdb.pfam['pdb_chain'].isin(chains)]
        self.lpdb.ec = self.lpdb.ec[self.lpdb.ec['pdb_chain'].isin(chains)]
        self.lpdb.cath = self.lpdb.cath[self.lpdb.cath['pdb_chain'].isin(chains)]
        self.lpdb.scop = self.lpdb.scop[self.lpdb.scop['pdb_chain'].isin(chains)]

    def _filter_structures(self, structures):
        self.lpdb.pfam = self.lpdb.pfam[self.lpdb.pfam['pdb'].isin(structures)]
        self.lpdb.ec = self.lpdb.ec[self.lpdb.ec['pdb'].isin(structures)]
        self.lpdb.cath = self.lpdb.cath[self.lpdb.cath['pdb'].isin(structures)]
        self.lpdb.scop = self.lpdb.scop[self.lpdb.cath['pdb'].isin(structures)]

    def _reset(self):
        del self.lpdb.pfam
        del self.lpdb.ec
        del self.lpdb.cath
        del self.lpdb.scop
        self.lpdb._remove_attr('pfam')
        self.lpdb._remove_attr('ec')
        self.lpdb._remove_attr('cath')
        self.lpdb._remove_attr('scop')
        self._load()
