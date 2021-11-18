import os
import importlib
import tarfile
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from localpdb import PDBVersioneer
from localpdb.utils.prot import parse_pdb_data
from localpdb.utils.os import parse_simple, custom_warning
from localpdb.utils.config import Config
from localpdb.utils.rest_api import CommandFactory

warnings.showwarning = custom_warning

class PDB:

    def __init__(self, db_path='', version='latest', plugins=[], auto_filter=True):
        """
        @param db_path (str): location of the localpdb database
        @param version (int) or 'latest': version of the localpdb database to load (default: version='latest')
        @param plugins (list): plugins to load (default=None)
        @param auto_filter (bool): automatically propagate selections performed on any of the DataFrames
        to other DataFrames
        (default: auto_filter=True)
        """

        self.db_path = Path(os.path.realpath(db_path)) # Absolute db path
        self.auto_filter = auto_filter # Flag to set auto-filtering feature
        self._pdbv = PDBVersioneer(db_path=db_path) # Versioning system
        self._loaded_plugins = []  # List of loaded plugins
        self._loaded_plugins_handles = []  # Handles to loaded plugins for reset function
        self.__registered_attrs = []  # Attributes handled by plugins
        self.__lock = False  # Lock flag used with auto-filtering to avoid recursive filtering

        # Check with PDBVersioneer whether any versions are installed in the db_path
        if len(self._pdbv.local_pdb_versions) == 0 and self._pdbv.current_local_version is None:
            raise FileNotFoundError(f'localpdb is not setup in directory \'{self.db_path}\'!')

        if version == 'latest':
            self.version = self._pdbv.current_local_version
        else:
            self.version = version

        if not isinstance(self.version, int):
            raise ValueError('localpdb version must be specified in numeric format!')
        if int(self.version) not in self._pdbv.local_pdb_versions:
            raise ValueError(f'Version \'{int(self.version)}\' is not available in the localpdb database!')

        try:
            self.__config = Config(self.db_path / 'config.yml').data
        except FileNotFoundError:
            raise FileNotFoundError(f'localpdb config file is available in directory \'{self.db_path}\'!')

        # Check if files are stored in the proper dir (double check with PDBVersionner which does that during download)
        self._working_path = f'{self.db_path}/data/{self.version}'  # Working path for the set version
        self._pdb_bundles_fn = f'{self._working_path}/pdb_bundles.txt'
        self._pdb_entries_type_fn = f'{self._working_path}/pdb_entries_type.txt'
        self._pdb_entries_fn = f'{self._working_path}/pdb_entries.txt'
        self._pdb_res_fn = f'{self._working_path}/pdb_resolution.txt'
        self._pdb_seqres_fn = f'{self._working_path}/pdb_seqres.txt.gz'
        if not all(os.path.isfile(fn) for fn in [self._pdb_bundles_fn, self._pdb_entries_fn, self._pdb_res_fn,
                                                 self._pdb_seqres_fn]):
            raise ValueError(
                'Not all PDB raw files for version \'{}\' exist! Try rerunning setup or update scripts!'.format(
                    self.version))
        self.bundles = parse_simple(self._pdb_bundles_fn)

        # Create dataframes with per-structure and per-chain data
        self.__entries, self.__chains = parse_pdb_data(self._pdb_entries_fn, self._pdb_entries_type_fn,
                                                       self._pdb_res_fn, self._pdb_seqres_fn)

        # Basic check for corrupt files
        if self.__entries.shape[1] not in [3, 4]: # Backwards compatibility with ver 0.1
            raise ValueError(
                f'PDB raw files for version \'{self.version}\' are corrupt! Try rerunning setup or update scripts!')

        # Set according filenames pointing to the structures
        id_dict = {id_: id_ for id_ in self.__entries.index.values}
        if self.__config['struct_mirror']['pdb'] and self.__config['struct_mirror']['pdb_init_ver'] <= self.version:
            self._set_filenames(id_dict, format='pdb')
        if self.__config['struct_mirror']['cif'] and self.__config['struct_mirror']['cif_init_ver'] <= self.version:
            self._set_filenames(id_dict, format='mmCIF')

        # Keep copy of dataframes to allow for reseting the selections
        self.__entries_copy = self.__entries.copy()
        self.__chains_copy = self.__chains.copy()

        # Workaround to run setters only once
        self.chains = self.__chains
        self.entries == self.__entries
        self.__rest_api_commands = CommandFactory()

        # Load plugins if any
        for plugin in plugins:
            self.load_plugin(plugin)

    def __setattr__(self, item, value):
        """
        This is a setattr hook that allows for the auto-filtering option. Whenever and attribute registered in
        __registered_attrs list is changed it triggers the update on the registered DataFrames from other plugins and
        lpdb.structures and lpdb.chains. Lock mechanism (self.__lock flag) is implemented to avoid recursive updates.
        """
        try: # This try is necessary because at init there are no set attributes
            if self.auto_filter:
                # Item must be in __registered_attrs and lpdb must have this attribute prior to auto-filtering
                if item in self.__registered_attrs and hasattr(self, item):
                    # Current pdb and pdb_chain indexes from lpdb.structures and lpdb.chains
                    pdb_ids, pdb_chain_ids = self._get_current_indexes()
                    # Now fetching pdb and pdb_chain ids from the plugin (it may not have certain columns so try/except)
                    try:
                        plugin_pdb_ids = set(value['pdb'])
                    except KeyError:
                        plugin_pdb_ids = set()
                    try:
                        plugin_pdb_chain_ids = set(value['pdb_chain'])
                    except KeyError:
                        plugin_pdb_chain_ids = set()

                    # Keep only pdb_ids that were in the lpdb.entries or lpdb.chains and are in the plugin
                    valid_pdb_ids = pdb_ids & plugin_pdb_ids
                    valid_pdb_chain_ids = pdb_chain_ids & plugin_pdb_chain_ids

                    # Update attributes donated by other plugins. Use self.__dict__ method to bypass the setattr hook
                    if not self.__lock:
                        for _attr in [el for el in self.__registered_attrs if el != item]:
                            try:
                                self.__dict__[_attr] = self.__dict__[_attr][
                                    self.__dict__[_attr]['pdb_chain'].isin(valid_pdb_chain_ids)]
                            except KeyError:
                                pass  # No such column in df attribute - do nothing
                            try:
                                self.__dict__[_attr] = self.__dict__[_attr][self.__dict__[_attr]['pdb'].isin(valid_pdb_ids)]
                            except KeyError:
                                pass  # No such column in df attribute - do nothing
                    # If there's no lock update also lpdb.structures and lpdb.chains
                        self.__entries = self.__entries[self.__entries.index.isin(valid_pdb_ids)]
                        self.__chains = self.__chains[self.__chains.index.isin(valid_pdb_chain_ids)]
        except AttributeError:
            pass
        super().__setattr__(item, value) # Now finally set the attribute

    def _register_attr(self, attr):
        """
        Registers attribute donated by the Plugin to allow auto-filtering option
        :param attr: attribute name to be reqistered
        """
        if attr not in self.__registered_attrs:
            self.__registered_attrs.append(attr)
        else:
            raise ValueError(f'Attribute \'{attr}\' was already registered by other plugin!')

    def _remove_attr(self, attr):
        """
        Removes the attribute donated by the Plugin to allow auto-filtering option
        :param attr: attribute name to be reqistered
        """
        if attr in self.__registered_attrs:
            self.__registered_attrs.remove(attr)
        else:
            raise ValueError(f'Attribute \'{attr}\' is not registered!')

    def __repr__(self):
        return f'localpdb database (v{self.version}) holding {len(self.entries)} entries ({len(self.chains)} chains)'

    def load_plugin(self, plugin):
        if plugin in self._loaded_plugins:
            raise RuntimeError('Plugin \'{}\' was already loaded!'.format(plugin))
        else:
            try:
                Plugin = getattr(importlib.import_module('localpdb.plugins.{}'.format(plugin)), plugin)
                pl = Plugin(self) #**plugin_kwargs
                pl.load()
                self._loaded_plugins_handles.append(pl)
            except ModuleNotFoundError:
                raise ValueError('Plugin \'{}\'is not installed!'.format(plugin))

    def _set_filenames(self, id_dict, format='pdb'):
        id_dict, a = self._pdbv.adjust_pdb_ids(id_dict, version=self.version)
        if format == 'pdb':
            fns = {pdb_id: f'{self.db_path}/mirror/pdb/{pdb_id[1:3]}/pdb{id_dict[pdb_id]}.ent.gz' if os.path.isfile(
                f'{self.db_path}/mirror/pdb/{pdb_id[1:3]}/pdb{id_dict[pdb_id]}.ent.gz') else 'not_compatible' if pdb_id in self.bundles else np.nan
                   for pdb_id in id_dict.keys()}
            self._add_col_structures(fns, ['pdb_fn'])
        if format == 'mmCIF':
            fns = {pdb_id: f'{self.db_path}/mirror/mmCIF/{pdb_id[1:3]}/{id_dict[pdb_id]}.cif.gz' if os.path.isfile(
                f'{self.db_path}/mirror/mmCIF/{pdb_id[1:3]}/{id_dict[pdb_id]}.cif.gz') else np.nan
                   for pdb_id in id_dict.keys()}
            self._add_col_structures(fns, ['mmCIF_fn'])

    def select_updates(self, mode='am+'):
        """
        Selects entries that were added or modified when compare to previous PDB release.
        @param mode: Select entries that were added ("a"), modified ("m"). "+" loads new entries compared to the
        previous localpdb version (important when localpdb is not updated weekly). If "+" is missing only new entries
        present in weekly PDB release will be selected.
        """
        map = {'a': 'added', 'm': 'modified_major'}
        ids = set()
        if not ('a' in mode or 'm' in mode):
            raise ValueError('Either \'a\' or \'m\' must be included in \'mode\'!')
        for m in ['a', 'm']:
            if m in mode:
                fn = f'{self.db_path}/data/{self.version}/{map[m]}.txt'
                if '+' in mode:
                    if os.path.isfile(f'{self.db_path}/data/{self.version}/{map[m]}_merged.txt'):
                        fn = f'{self.db_path}/data/{self.version}/{map[m]}_merged.txt'
                    else:
                        raise RuntimeError(f'\'+\' is not compatible with \'{map[m]}\' mode and localpdb version \'{self.version}\'')
                with open(fn) as f:
                    tmp_ids = {line.rstrip() for line in f}
                    ids = ids | tmp_ids
        curr_ids = set(self.entries.index.values)
        self.entries = self.entries.loc[ids & curr_ids]

    def reset(self):
        """
        Resets the selections done on lpdb.structures and lpdb.chains and restores the initial state of the localpdb.
        """
        del self.__entries
        del self.__chains
        self.__entries = self.__entries_copy.copy()
        self.__chains = self.__chains_copy.copy()
        for ph in self._loaded_plugins_handles:
            ph._reset()

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
            new_pdb_chain_ids = set(chains.index.tolist())
            self.__entries = self.__entries[self.__entries.index.isin(new_pdb_ids)]
            self.__lock = True
            for ph in self._loaded_plugins_handles:
                ph._filter_chains(new_pdb_chain_ids)
            self.__lock = False
        self.__chains = chains

    @entries.setter
    def entries(self, entries):
        if self.auto_filter:
            new_pdb_ids = set(entries.index.tolist())
            self.__chains = self.__chains[self.__chains['pdb'].isin(new_pdb_ids)]
            self.__lock = True
            for ph in self._loaded_plugins_handles:
                ph._filter_entries(new_pdb_ids)
            self.__lock = False
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

    def search_seq_motif(self, query, type_='prosite', return_type="entry", no_hits=1000, select=False):
        """
        Get dataframe with pdb ids having sequence matching given sequence motif
        :param query: (str) motif to find in pdb sequences, according to given type_ (i.e prosite)
        :param type_: (str) name of type of query
        :param return_type: (str) type of returned data
        :param no_hits: (int) number of hits to fetch, -1 for all results
        :param select: (bool) if True results of the query will be propagated to either lpdb.entries or lpdb.chains
        (depending on the return_type parameter)
        :return: pd.DataFrame
        """
        results = self.__rest_api_commands.get('seqmotif')(query, type_,
                                                           resp_type=return_type,
                                                           rows=no_hits).execute()
        if select:
            if return_type == 'entry':
                self.entries = self.entries[self.entries.index.isin(results.index)]
            elif return_type == 'polymer_instance':
                self.chains = self.chains[self.chains.index.isin(results.index)]
        else:
            return results

    def search_seq(self, sequence, evalue=1, identity=0.9, return_type="polymer_instance",
                   no_hits=1000, select=False):
        """
        Get dataframe with pdb ids have sequence similar to given sequence
        :param sequence: (str) sequence used to fin similar ones
        :param evalue: (float) minimum e value
        :param identity: (float) minimum identity to input sequence
        :param return_type: (str) type of returned data
        :param no_hits: (int) number of hits to fetch, -1 for all results
        :param select: (bool) if True results of the query will be propagated to either lpdb.entries or lpdb.chains
        (depending on the return_type parameter)
        :return: pd.DataFrame
        """
        results = self.__rest_api_commands.get('sequence')(sequence, evalue, identity,
                                                           resp_type=return_type, rows=no_hits).execute()
        if select:
            if return_type == 'entry':
                self.entries = self.entries[self.entries.index.isin(results.index)]
            elif return_type == 'polymer_instance':
                self.chains = self.chains[self.chains.index.isin(results.index)]
        else:
            return results

    def search_struct(self, pdb_id, assembly_id=1, operator='strict_shape_match',
                      return_type="entry", no_hits=1000, select=False):
        """
        Get dataframe with pdb ids having structure similar to structure of given pdb_id
        :param pdb_id: (str) pdb id (i.e 2mnr)
        :param assembly_id: (int) assembly number
        :param operator: (str) match mode type either relaxed_shape_match or strict_shape_match
        :param return_type: (str) type of returned data
        :param no_hits: (int) number of hits to fetch, -1 for all results
        :param select: (bool) if True results of the query will be propagated to either lpdb.entries or lpdb.chains
        (depending on the return_type parameter)
        :return: pd.DataFrame
        """
        results = self.__rest_api_commands.get('structure')(pdb_id, assembly_id, operator,
                                                            resp_type=return_type, rows=no_hits).execute()
        if select:
            if return_type == 'entry':
                self.entries = self.entries[self.entries.index.isin(results.index)]
            elif return_type == 'polymer_instance':
                self.chains = self.chains[self.chains.index.isin(results.index)]
        else:
            return results

    def search_struct_motif(self, pdb_id, residue_ids, score_cutoff=0, exchanges=None,
                            return_type="entry", no_hits=1000, select=False):
        """
        Get dataframe with pdb ids having structure motif similar to one defined for pdb_id
        :param pdb_id: (str) pdb id (i.e 2mnr)
        :param residue_ids: (list(dict,)) definition of motif
        :param score_cutoff: (int) return matches having scores greater than this value
        :param exchanges: (list(dict,)) definition of allowed amino acids for given residue_ids
        :param return_type: (str) type of returned data
        :param no_hits: (int) number of hits to fetch, -1 for all results
        :param select: (bool) if True results of the query will be propagated to either lpdb.entries or lpdb.chains
        (depending on the return_type parameter)
        :return: pd.DataFrame
        """
        results = self.__rest_api_commands.get('strucmotif')(pdb_id, residue_ids, score_cutoff, exchanges,
                                                             resp_type=return_type, rows=no_hits).execute()
        if select:
            if return_type == 'entry':
                self.entries = self.entries[self.entries.index.isin(results.index)]
            elif return_type == 'polymer_instance':
                self.chains = self.chains[self.chains.index.isin(results.index)]
        else:
            return results

    def search(self, attribute, operator, value, return_type='entry', no_hits=1000, get_doc_only=False, select=False):
        """
        Get dataframe with results from search for value of given attribute
        :param attribute: (str) attribute to search for
        :param operator: (int) operator to filter attribute by value i.e greater, in etc
        :param value: (str) value of given attribute
        :param return_type: (str) type of returned data
        :param no_hits: (int) number of hits to fetch, -1 for all results
        :param get_doc_only: (bool) if True get datafarame with description of possible attributes and operators
        :param select: (bool) if True results of the query will be propagated to either lpdb.entries or lpdb.chains
        (depending on the return_type parameter)
        :return: pd.DataFrame
        """
        command = self.__rest_api_commands.get('text')(attribute, operator, value,
                                                       resp_type=return_type, rows=no_hits)
        if get_doc_only:
            return command.get_doc()
        results = command.execute()
        if select:
            if return_type == 'entry':
                self.entries = self.entries[self.entries.index.isin(results.index)]
            elif return_type == 'polymer_instance':
                self.chains = self.chains[self.chains.index.isin(results.index)]
        else:
            return results

    def extract(self, out_fn):
        if self.__config['struct_mirror']['pdb']:
            warnings.warn('Extracting localpdb data is not compatible with the structure files mirror in PDB format!')
        with tarfile.open(out_fn, mode='w:gz') as arch:
            arch.add(self._working_path, arcname='/'.join(self._working_path.split('/')[-2:]))

    def _get_current_indexes(self):
        """
        Returns current indexes of the structures and chains dataframes.
        :return: set with structure df indexes and set with chains df indexes
        """
        pdb_ids = set(self.__entries.index)
        pdb_chain_ids = set(self.__chains.index)
        return pdb_ids, pdb_chain_ids
