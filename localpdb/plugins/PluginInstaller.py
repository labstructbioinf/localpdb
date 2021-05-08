import importlib
import logging
from localpdb import PDB
from .PluginVersioneer import PluginVersioneer

logger = logging.getLogger(__name__)


class PluginInstaller:

    def __init__(self, plugins, db_path, pdbv):
        """
        Wrapper around the plugin installing methods to avoid replication of the code between localpdb_setup and update scripts
        :param plugin: (list) Plugins to setup / update
        :param db_path: localpdb db location
        :param pdbv: instance of the PDBVersioneer
        """
        self.pdbv = pdbv
        self.versions = set(self.pdbv.local_pdb_versions)

        self.plugins = plugins
        self.db_path = db_path

    def _setup(self, Plugin, version):
        """
        Wrapper for the plugin setup
        :param plugin: plugin to setup
        :param version: localpdb version
        :return:
        """
        lpdb = PDB(self.db_path, version=version)  # Load localpdb for the specified version
        pl = Plugin(lpdb)  # Initialize the plugin with the localpdb instance
        for req_pl in pl.required_plugins:  # Load required plugins if specified
            try:
                pl.lpdb.load_plugin(req_pl)
                logger.debug(
                    f'Loaded required dependency \'{req_pl}\' for the plugin \'{plugin}\', version \'{version}\'')
            except ValueError:
                logger.error(
                    f'Failed to load required dependency \'{req_pl}\' for the plugin \'{plugin}\', version \'{version}\'')
        pl._prep_paths()  # Prepare path(s) required by the plugin
        res = pl.setup() if int(version) == self.pdbv.first_local_version else pl.update()
        return res

    def setup(self):
        """
        Setup for all specified plugins and current localpdb local versions
        """
        for plugin in self.plugins:
            try:
                print()  # Assure spacing between the messages for separate plugins
                logger.info(f'Setting up plugin \'{plugin}\'...')

                Plugin = getattr(importlib.import_module('localpdb.plugins.{}'.format(plugin)),
                                 plugin)  # Load plugin def
                plugin_dir = self.db_path / Plugin.plugin_dir  # Absolute directory where plugins are stored

                # Determine for which versions of localpdb plugin should be installed
                plv = PluginVersioneer(plugin_dir)
                versions = (self.versions - plv.installed_plugin_versions)
                if Plugin.no_history:
                    logger.warning(f'Plugin \'{plugin}\' does not support the history versioning. ' \
                                   'Only version corresponding to the current PDB release can be installed!')
                    versions = versions & {self.pdbv.current_local_version}

                if len(versions) > 0:  # There are localpdb version for which plugin can be installed

                    for version in versions:
                        logger.debug(f'Setting up plugin \'{plugin}\' for the localpdb version \'{version}\'')
                        result = self._setup(Plugin, version)
                        if result == 0:
                            logger.info(f'Successfully set up plugin \'{plugin}\' for the localpdb version \'{version}\'')
                        else:
                            logger.error(f'Could not set up plugin \'{plugin}\' for the localpdb version \'{version}\'')

                else:
                    logger.info(f'Plugin \'{plugin}\' is already setup for all available localpdb versions!')
            except ModuleNotFoundError:
                logger.error(f'Plugin \'{plugin}\' is not installed properly!')
