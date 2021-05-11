import os
import importlib
import pandas as pd
import numpy as np
from pathlib import Path
from localpdb import PDBVersioneer
from localpdb.utils.prot import parse_pdb_data
from localpdb.utils.config import Config


class PDB:

    def __init__(self, db_path='', version='latest', auto_filter=True):

        self.db_path = Path(os.path.realpath(db_path)) # Absolute db path
        self.auto_filter = auto_filter # Flag to set auto-filtering feature
        self.__pdbv = PDBVersioneer(db_path=db_path) # Versioning system
        self._loaded_plugins = []  # List of loaded plugins
        self._loaded_plugins_handles = []  # Handles to loaded plugins for reset function
        self.__registered_attrs = []  # Attributes handled by plugins
        self.__lock = False  # Lock flag used with auto-filtering to avoid recursive filtering

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
            self.__config = Config(self.db_path / 'config.yml').data
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
        if self.__entries.shape[1] not in [3, 4]: # Backwards compatibility with ver 0.1
            raise ValueError(
                f'PDB raw files for version \'{self.version}\' are corrupt! Try rerunning setup or update scripts!')

        # Set according filenames pointing to the structures
        if self.__config['struct_mirror']['pdb'] and self.__config['struct_mirror']['pdb_init_ver'] <= version:
            self.__entries['pdb_fn'] = self.__entries.index.map(
                lambda x: f'{self.db_path}/mirror/pdb/{x[1:3]}/pdb{x}.ent.gz' if os.path.isfile(
                    f'{self.db_path}/mirror/pdb/{x[1:3]}/pdb{x}.ent.gz') else np.nan)
        if self.__config['struct_mirror']['cif'] and self.__config['struct_mirror']['cif_init_ver'] <= version:
            self.__entries['mmcif_fn'] = self.__entries.index.map(
                lambda x: f'{self.db_path}/mirror/mmCIF/{x[1:3]}/{x}.cif.gz' if os.path.isfile(
                    f'{self.db_path}/mirror/mmCIF/{x[1:3]}/{x}.cif.gz') else np.nan)

        # Keep copy of dataframes to allow for reseting the selections
        self.__entries_copy = self.__entries.copy()
        self.__chains_copy = self.__chains.copy()

        # Workaround to run setters only once
        self.chains = self.__chains
        self.entries == self.__entries

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
            raise ValueError('Attribute \'{}\' was already registered by other plugin!'.format(attr))

    def __repr__(self):
        return f'localpdb database (v{self.version}) holding {len(self.entries)} entries ({len(self.chains)} chains)'

    def load_plugin(self, plugin, plugin_kwargs=dict()):
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
            new_pdb_chain_ids = set(chains.index.tolist())
            self.__entries = self.__entries[self.__entries.index.isin(new_pdb_ids)]
            self.__lock = True
            for ph in self._loaded_plugins_handles:
                ph._filter_chains(new_pdb_chain_ids)
            self.__lock = False

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

    def _get_current_indexes(self):
        """
        Returns current indexes of the structures and chains dataframes.
        :return: set with structure df indexes and set with chains df indexes
        """
        pdb_ids = set(self.__entries.index)
        pdb_chain_ids = set(self.__chains.index)
        return pdb_ids, pdb_chain_ids
