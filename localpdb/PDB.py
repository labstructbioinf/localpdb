import os

import numpy as np
import pandas as pd

from localpdb import PDBVersioneer
from localpdb.utils.config import Config
from localpdb.utils.prot import parse_pdb_data
from localpdb.utils.search_api.search import SearchMotifCommand, SequenceSimilarityCommand, StructureSimilarityCommand


class PDB:

    def __init__(self, db_path='', version='latest', auto_filter=True):

        self.db_path = os.path.realpath(db_path)  # Absolute db path
        self.auto_filter = auto_filter  # Flag to set auto-filtering feature
        self.__pdbv = PDBVersioneer(db_path=db_path)  # Versioning system

        # Check with PDBVersioneer whether any versions are installed in the db_path
        if len(self.__pdbv.local_pdb_versions) == 0 and self.__pdbv.current_local_version is None:
            raise FileNotFoundError(f'localpdb is not setup in directory \'{self.db_path}\'!')

        if version == 'latest':
            self.version = self.__pdbv.current_local_version
        else:
            self.version = version

        if not isinstance(self.version, int):
            raise ValueError('localpdb version must be specified in numeric format!')
        if int(self.version) not in self.__pdbv.local_pdb_versions:
            raise ValueError('Version \'{}\' is not available in the localpdb database!')

        try:
            config = Config(self.db_path)
            self.__config = config.data
        except FileNotFoundError:
            raise FileNotFoundError(f'localpdb config file is available in directory \'{self.db_path}\'!')

        # Check if files are stored in the proper dir (double check with PDBVersionner which does that during download)
        self.__working_path = f'{self.db_path}/data/{self.version}'  # Working path for the set version
        pdb_bundles_fn = '{}/pdb_bundles.txt'.format(self.__working_path)
        pdb_entries_type_fn = "{}/pdb_entries_type.txt".format(self.__working_path)
        pdb_entries_fn = "{}/pdb_entries.txt".format(self.__working_path)
        pdb_res_fn = "{}/pdb_resolution.txt".format(self.__working_path)
        pdb_seqres_fn = "{}/pdb_seqres.txt.gz".format(self.__working_path)
        if not all(os.path.isfile(fn) for fn in [pdb_bundles_fn, pdb_entries_fn, pdb_res_fn, pdb_seqres_fn]):
            raise ValueError(
                'Not all PDB raw files for version \'{}\' exist! Try rerunning setup or update scripts!'.format(
                    self.version))

        # Create dataframes with per-structure and per-chain data
        self.__entries, self.__chains = parse_pdb_data(pdb_entries_fn, pdb_entries_type_fn, pdb_res_fn, pdb_seqres_fn)

        # Basic check for corrupt files
        if self.__entries.shape[1] != 4:
            raise ValueError(
                f'PDB raw files for version \'{self.version}\' are corrupt! Try rerunning setup or update scripts!')

        # Set according filenames pointing to the structures
        if self.__config['mirror_pdb']:
            self.__entries['pdb_fn'] = self.__entries.index.map(
                lambda x: f'{self.db_path}/mirror/pdb/{x[1:3]}/pdb{x}.ent.gz' if os.path.isfile(
                    f'{self.db_path}/mirror/pdb/{x[1:3]}/pdb{x}.ent.gz') else np.nan)
        if self.__config['mirror_cif']:
            self.__entries['mmcif_fn'] = self.__entries.index.map(
                lambda x: f'{self.db_path}/mirror/mmCIF/{x[1:3]}/{x}.cif.gz' if os.path.isfile(
                    f'{self.db_path}/mirror/mmCIF/{x[1:3]}/{x}.cif.gz') else np.nan)

        # Keep copy of dataframes to allow for reseting the selections
        self.__entries_copy = self.__entries.copy()
        self.__chains_copy = self.__chains.copy()

        # Workaround to run setters only once
        self.chains = self.__chains
        self.entries == self.__entries

    def __repr__(self):
        return f'localpdb database (v{self.version}) holding {len(self.entries)} entries ({len(self.chains)} chains)'

    def select_updates(self):
        """
        Selects only new entries that were added during the last PDB update
        """
        with open('{}/data/{}/added.txt'.format(self.db_path, self.version)) as f:
            idents = [line.rstrip() for line in f.readlines()]
        curr_idx = set(self.entries.index.values)
        pdb_ids_clean = [ident for ident in idents if ident in curr_idx]
        self.entries = self.entries.loc[pdb_ids_clean]

    def reset(self):
        """
        Resets the selections done on lpdb.structures and lpdb.chains and restores the initial state of the localpdb.
        """
        del self.__entries
        del self.__chains
        self.__entries = self.__entries_copy.copy()
        self.__chains = self.__chains_copy.copy()

    @property
    def chains(self):
        return self.__chains

    @property
    def entries(self):
        return self.__entries

    @chains.setter
    def chains(self, chains):
        if self.auto_filter:
            new_pdb_ids = set(chains['pdb'].tolist())
            self.__entries = self.__entries[self.__entries.index.isin(new_pdb_ids)]
        self.__chains = chains

    @entries.setter
    def entries(self, entries):
        if self.auto_filter:
            new_pdb_ids = set(entries.index.tolist())
            self.__chains = self.__chains[self.__chains['pdb'].isin(new_pdb_ids)]
        self.__entries = entries

    def _add_col_structures(self, data, added_col_name=[]):
        if len(set(added_col_name) & set(self.__entries.columns)) > 0:
            raise ValueError('At least one added column name is already present in \'lpdb.structures\' df!')
        if isinstance(data, dict):
            data = pd.DataFrame.from_dict({key: [value] for key, value in data.items()}, orient='index',
                                          columns=added_col_name)
        self.__entries = pd.merge(self.entries, data, left_index=True, right_index=True, how='left')

    def _add_col_chains(self, data, added_col_name=[]):
        if len(set(added_col_name) & set(self.__chains.columns)) > 0:
            raise ValueError('At least one added column name is already present in \'lpdb.chains\' df!')
        if isinstance(data, dict):
            data = pd.DataFrame.from_dict({key: [value] for key, value in data.items()}, orient='index',
                                          columns=added_col_name)
        self.__chains = pd.merge(self.chains, data, left_index=True, right_index=True, how='left')

    def search_seq_motif(self, query, type_='prosite'):
        """
        Get dataframe with pdb ids having sequence matching given sequence motif
        :param query: (str) motif to find in pdb sequences, according to given type_ (i.e prosite)
        :param type_: (str) name of type of query
        :return: pd.DataFrame
        """
        command = SearchMotifCommand(query, type_)
        return command.execute()

    def search_seq(self, sequence, evalue=1, identity=0.9):
        """
        Get dataframe with pdb ids have sequence similar to given sequence
        :param sequence: (str) sequence used to fin similar ones
        :param evalue: (float) minimum e value
        :param identity: (float) minimum identity to input sequence
        :return: pd.DataFrame
        """
        command = SequenceSimilarityCommand(sequence, evalue, identity)
        return command.execute()

    def search_struct(self, pdb_id, assembly_id=1, operator='strict_shape_match'):
        """
        Get dataframe with pdb ids having structure similar to structure of given pdb_id
        :param pdb_id: (str) pdb id (i.e 2mnr)
        :param assembly_id: (int) assembly number
        :param operator: (str) match mode type either relaxed_shape_match or strict_shape_match
        :return: pd.DataFrame
        """
        command = StructureSimilarityCommand(pdb_id, assembly_id, operator)
        return command.execute()
