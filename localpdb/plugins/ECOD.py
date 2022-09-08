import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
import pandas as pd
import urllib.request
from bs4 import BeautifulSoup


class ECOD(Plugin):

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
        # Load ecod dataframe
        ecod_fn = 'ecod_domains_{}.txt'.format(self.plugin_version)
        tmp_df = pd.read_csv(str(self.plugin_dir) + '/data/' + ecod_fn, sep='\t', skiprows=4, index_col=1)
        tmp_df = tmp_df[tmp_df['chain'] != '.']
        tmp_df['pdb_chain'] = tmp_df['pdb'] + '_' + tmp_df['chain']
        del tmp_df['chain']
        del tmp_df['asm_status']
        del tmp_df['manual_rep']
        del tmp_df['#uid']
        cols = tmp_df.columns.tolist()
        tmp_df = tmp_df[[cols[-1]] + [cols[0]] + cols[3:-1] + cols[1:3]]
        cols = [x if x != 'f_id' else 'ecod_number' for x in tmp_df.columns]
        tmp_df.columns = cols
        tmp_df['x_id'] = tmp_df['ecod_number'].apply(lambda x: x.split('.')[0])
        tmp_df['h_id'] = tmp_df['ecod_number'].apply(lambda x: x.split('.')[1])
        tmp_df['t_id'] = tmp_df['ecod_number'].apply(lambda x: x.split('.')[2])
        tmp_df['f_id'] = tmp_df['ecod_number'].apply(lambda x: x.split('.')[3] if len(x.split('.')) == 4 else 0)

        _, pdb_chain_ids = self.lpdb._get_current_indexes()
        tmp_df = tmp_df[tmp_df['pdb_chain'].isin(pdb_chain_ids)] # Select entries that are only in the lpdb.chains
        self.lpdb._register_attr('ecod') # Register new attribute
        self.lpdb.ecod = tmp_df # Set the attribute

    def _setup(self):
        try:
            local_fn = str(self.plugin_dir) + '/data/ecod_domains_{}.txt'.format(self.plugin_version)
            download_url(self.history[self.plugin_version], local_fn)
        except:
            raise PluginInstallError()

    def _get_historical_versions(self):
        # Fetch ECOD history
        ecod_content = urllib.request.urlopen(self.plugin_config['ecod_url'])
        soup = BeautifulSoup(ecod_content, "html.parser")
        ecod_history = {}
        for ultag in soup.find('div', class_='history').find_all('ul'):
            for litag in ultag.find_all('li')[:-1]:
                ver_url = self.plugin_config['ecod_domain'] + litag.find('a')['href']
                version = int(str(litag.text).split(' ')[0])
                ecod_history[version] = ver_url # ECOD history dict
        return ecod_history

    def _filter_chains(self, chains):
        self.lpdb.ecod = self.lpdb.ecod[self.lpdb.ecod['pdb_chain'].isin(chains)]

    def _filter_entries(self, structures):
        self.lpdb.ecod = self.lpdb.ecod[self.lpdb.ecod['pdb'].isin(structures)]

    def _reset(self):
        del self.lpdb.ecod
        self.lpdb._remove_attr('ecod')
        self._load()
