import warnings
import logging
import shutil
import os
from .PluginVersioneer import PluginVersioneer
from localpdb.utils.os import create_directory, custom_warning
from localpdb.utils.errors import *

logger = logging.getLogger(__name__)
warnings.showwarning = custom_warning

class Plugin:

    def __init__(self, lpdb):
        """
        Generic class for the localpdb plugins
        :param lpdb: instance of the localpdb.PDB
        """
        # Init routine
        self.lpdb = lpdb # Instance of the PDB object
        self.plugin_dir = self.lpdb.db_path / self.plugin_dir  # Modify plugin dir to yield absolute path
        self.plv = PluginVersioneer(self.plugin_dir)  # Initialize PluginVersioneer
        # Set plugin_version to load - by default this is equal to lpdb.version
        # However, if plugin_config['allow_loading_outdated'] is True, will try to find closes earlier installed plugin version
        # self.plugin_version will remain None if there is not suitable installed plugin version to load
        self.plugin_version = None
        self.set_version(self.plv.installed_plugin_versions)
        self.history = self._get_historical_versions()
        self.cp_files = []
        if self.plugin_config['requires_pdb'] or self.plugin_config['requires_cif']:
            self.id_dict, self.map_dict = self.lpdb._pdbv.adjust_pdb_ids({id_: id_ for id_ in self.lpdb.entries.index},
                                                                          self.plugin_version)

    def load(self):
        # Generic loader for plugins. Calls individual plugin _load method
        if self.plugin_version is not None:
            if self.plugin_version != self.lpdb.version:
                warnings.warn(
                    f'Loaded version of the plugin \'{self.plugin_name}\' ({self.plugin_version}) does not match the localpdb version ({self.lpdb.version}). '
                    f'Data may not be fully accurate.')
            self._load()
            self.lpdb._loaded_plugins.append(self.plugin_name) # Add to loaded plugins
        else:
            # Customize error warning based on self.plugin_config['allow_loading_outdated']
            if self.plugin_config['allow_loading_outdated']:
                raise RuntimeError(
                    f'Plugin \'{self.plugin_name}\' is not set up neither for localpdb version \'{self.lpdb.version}\' nor its previous versions!')
            else:
                raise RuntimeError(
                    f'Plugin \'{self.plugin_name}\' is not set up for localpdb version \'{self.lpdb.version}\'!')

    def update(self):
        if self.plugin_config['requires_pdb'] or self.plugin_config['requires_cif']:
            if self.plugin_config['requires_pdb']:
                self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['pdb_fn'].notnull()]
                self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['pdb_fn'] != 'not_compatible']
            if self.plugin_config['requires_cif']:
                self.lpdb.entries = self.lpdb.entries[self.lpdb.entries['mmCIF_fn'].notnull()]
            try:
                self.lpdb.select_updates(mode='am+')
            except RuntimeError:
                self.lpdb.select_updates(mode='am')
            for id_, updated_id in self.map_dict.items():
                org_fn = self.fn_schema.format(pdb_id=id_, plugin_dir=self.plugin_dir)
                dest_fn = self.fn_schema.format(pdb_id=updated_id, plugin_dir=self.plugin_dir)
                shutil.copy2(org_fn, dest_fn)
                self.cp_files.append((org_fn, dest_fn))
                logger.debug(f'Moved file\'{org_fn}\' to \'{dest_fn}\'.')
        return self.setup()

    def setup(self):
        """
        Generic function for plugin setup - calls individual plugin _setup() method
        :return:
        """
        # If historical versions of the plugin data are available and plugin permits outdated loading - try to setup
        # earlier versions if current one is not available
        if self.plugin_config['available_historical_versions'] and self.plugin_config['allow_loading_outdated']:
            self.set_version(list(self.history.keys()))
        if self.plugin_version not in self.plv.installed_plugin_versions:
            try:
                self._prep_paths()
                info = self._setup()
                self.plv.update_logs(version=self.plugin_version, additional_info=info)
                if self.plugin_version != self.lpdb.version:
                    logger.warning(f'Installed plugin \'{self.plugin_name}\' version \'{self.plugin_version}\'' +
                                   f' does not match localpdb (version \'{self.lpdb.version}\') however plugin permits it.' +
                                   ' This is typical for plugins handling the data that is not released in a weekly cycle.')
            except:
                self._cleanup()
                raise PluginInstallError()
        else:
            logger.warning(f'Installed plugin \'{self.plugin_name}\' version \'{self.plugin_version}\'' +
                           f' does not match localpdb (version \'{self.lpdb.version}\') however plugin permits it.' +
                           ' This is typical for plugins handling the data that is not released in a weekly cycle.')
            raise PluginAlreadyInstalledOutdated()

    def set_version(self, versions):
        """
        Version handler for plugins.
        @param versions: list of versions to check.
        @return: If plugin allows loading an outdated version (plugin_config['allow_loading_outdated'] is True), it returns closest
        historical version out of versions passed in the list. If not it should return the exact version matching the lpdb version.
        If no suitable version is found returns None.
        """
        if not self.plugin_config['allow_loading_outdated']:
            self.plugin_version = self.lpdb.version
        else:
            self.plugin_version = self.find_closest_historical_version(self.lpdb.version, versions)

    def _reset(self):
        self.load()

    def _cleanup(self):
        for org_fn, dest_fn in self.cp_files:
            try:
                print(org_fn, dest_fn)
                shutil.copy2(dest_fn, org_fn)
                logger.debug(f'Moved file\'{dest_fn}\' to \'{org_fn}\'.')
                os.remove(dest_fn)
            except FileNotFoundError:
                pass

    @staticmethod
    def find_closest_historical_version(version, versions):
        """
        Finds closest historical version in list of versions.
        @param version: specified version.
        @param versions: list of versions.
        @return: closest historical version.
        """
        diffs = {ver - version: ver for ver in versions if ver - version <= 0}
        return diffs[max(diffs, key=lambda key: diffs[key])] if len(diffs) > 0 else None

    def _get_historical_versions(self):
        return {self.lpdb.version: None}

    def _filter_chains(self, chains):
        pass

    def _filter_entries(self, structures):
        pass

    def _prep_paths(self):
        create_directory(f'{self.plugin_dir}/')
        create_directory(f'{self.plugin_dir}/data')