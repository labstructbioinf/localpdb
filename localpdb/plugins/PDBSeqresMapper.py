import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory
from localpdb.utils.network import download_url

logger = logging.getLogger(__name__)

# Plugin specific imports
import gzip
import json


class PDBSeqresMapper(Plugin):

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
        self.url = self.plugin_config['url']

    def _load(self):
        fn = f'{self.plugin_dir}/{self.plugin_version}.json.gz'
        with gzip.open(fn, 'rt') as f:
            tmp_dict = json.loads(f.read())
        self.lpdb._mapping_dict, self.lpdb.mapped_seqres_regions = self._unwrap_json(tmp_dict)
        self.lpdb.get_pdbseqres_mapping = self.get_pdbseqres_mapping.__get__(self)
        self.lpdb.map_pdb_feat_to_seqres = self.map_pdb_feat_to_seqres.__get__(self)

    def _setup(self):
        try:
            remote_fn = f'{self.url}/{self.plugin_version}.json.gz'
            local_fn = f'{self.plugin_dir}/{self.plugin_version}.json.gz'
            if not download_url(remote_fn, local_fn):
                logger.error(f'Plugin data is not currently available for localpdb version {self.plugin_version}. Try again later.')
                raise
        except:
            raise PluginInstallError()

    def _prep_paths(self):
        create_directory(f'{self.plugin_dir}/')

    def get_pdbseqres_mapping(self, pdb_chain_id, reverse=False):
        """
        Retrieves the mapping between the residues in the PDB structure and the PDB SEQRES sequence
        @param pdb_chain_id (str): pdb_chain identifier
        @param reverse (bool): reverse the order in returned dictionary.
        @return: dict mapping the PDB structure residue identifiers (str) to PDB SEQRES sequences indexes (int) or reverse
        dict if reverse is True
        """
        if pdb_chain_id not in self.lpdb._mapping_dict.keys():
            raise ValueError('Mapping for id \'{}\' is not available!'.format(pdb_chain_id))

        mapping = {}
        for pdb_res, seqres_res in self.lpdb._mapping_dict[pdb_chain_id].items():
            if '|' in pdb_res and '|' in seqres_res:
                key_start, key_stop = pdb_res.split('|')
                val_start, val_stop = seqres_res.split('|')
                for key_, value_ in zip(range(int(key_start), int(key_stop) + 1),
                                        range(int(val_start), int(val_stop) + 1)):
                    mapping[str(key_)] = value_
            else:
                mapping[str(pdb_res)] = seqres_res
        if reverse:
            return {value: key for key, value in mapping.items()}
        return mapping

    def map_pdb_feat_to_seqres(self, value_dict, pdb_chain_id, na_value=0, regions=False):
        """
        Maps pdb features onto the seqres sequence
        :param value_dict: Dict with PDB resnames as keys and arbitrary values
        :param pdb_chain_id: pdb_chain identifier
        :param na_value: format for the missing values in seqres (usually not all PDB resids are mapped onto seqres)
        :param regions: bool flag to return also continous seqres fragments corresponding to the continous fragments in PDB
        :return: list of length equal to seqres sequence with mapped PDB values
        """

        if pdb_chain_id not in self.lpdb._mapping_dict.keys():
            raise ValueError('Mapping for id \'{}\' is not available!'.format(pdb_chain_id))

        mapping_dict = self.get_pdbseqres_mapping(pdb_chain_id)
        seqres_seq = self.lpdb.chains.loc[pdb_chain_id, 'sequence']
        mapping = [na_value] * len(seqres_seq)

        for key, value in value_dict.items():
            if key in mapping_dict.keys():
                mapping[mapping_dict[key]] = value
        if regions:
            return mapping, self.lpdb.mapped_seqres_regions[pdb_chain_id]
        else:
            return mapping

    @staticmethod
    def _unwrap_json(_dict):
        mapping = {}
        seqres_regions = {}
        for key, values in _dict.items():
            seqres_regions[key] = values[1]
            mapping[key] = values[0]
        return mapping, seqres_regions
