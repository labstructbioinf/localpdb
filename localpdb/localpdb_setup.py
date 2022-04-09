#! /usr/bin/env python3
import os
import argparse
import logging
import sys
import shutil
import socket
import tarfile
import json
import ftplib
import importlib
from tqdm import tqdm
from pathlib import Path
from localpdb import PDB, PDBVersioneer, PDBDownloader
from localpdb.plugins import PluginVersioneer
from localpdb.utils.os import create_directory, setup_logging_handlers, clean_exit
from localpdb.utils.config import load_remote_source, Config
from localpdb.utils.errors import *

# Setup logging
fn_log, handlers = setup_logging_handlers(tmp_path='/tmp/')
logging.basicConfig(level=logging.DEBUG, handlers=handlers, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def get_params():
    # Parse arguments
    parser = argparse.ArgumentParser(description='localpdb setup/update script')
    parser.add_argument('-db_path', help='Path to store localpdb database', required=True, metavar='DB_PATH')
    parser.add_argument('-plugins', help='Names of plugins to set up', metavar='PLUGINS', nargs='+',
                        default=[])
    parser.add_argument('-mirror', help='''PDB mirror used to download the protein structures.
    Valid options are \'rcsb\' (RCSB PDB - US), \'pdbe\' (PDBe - UK) or \'pdbj\' (PDBj - Japan)''',
                        default='rcsb', metavar='MIRROR', choices=['rcsb', 'pdbe', 'pdbj'])
    parser.add_argument('--from_config', help='Setup localpdb database from the predefined config file.' \
                                            ' This enables recreation of the historical PDB versions from different sources.')
    parser.add_argument('--update', help='Update existing localpdb database', action='store_true')
    parser.add_argument('--fetch_pdb', help='Download the protein structures in the PDB format', action='store_true')
    parser.add_argument('--fetch_cif', help='Download the protein structures in the mmCIF format', action='store_true')
    parser.add_argument('-tmp_path', help='Path to store the temporary installation files', default='/tmp/', metavar='TMP_PATH')

    # Add optional arguments to manually define PDB mirror (these options override the mirror definition from -mirror)
    # Used mostly for testing purposes.
    parser.add_argument('-ftp_url', help=argparse.SUPPRESS)
    parser.add_argument('-rsync_url', help=argparse.SUPPRESS)
    parser.add_argument('-rsync_opts', help=argparse.SUPPRESS)
    parser.add_argument('-download_proto', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.db_path = Path(os.path.abspath(args.db_path))
    if args.update and any([args.fetch_pdb, args.fetch_cif, len(args.plugins) > 0]):
        print('\nOptions \'--update\' and any of the (\'--fetch_pdb\', \'--fetch_cif\', \'-plugins\')' 
              'are mutually exclusive!\n')
        parser.print_help()
        sys.exit(1)
    if args.from_config and any([args.fetch_pdb, len(args.plugins) > 0, args.update]):
        print('\nOptions \'--from_config\' and any of the (\'--update\', \'--fetch_pdb\','
              '\'-plugins\') are mutually exclusive!\n')
        parser.print_help()
        sys.exit(1)
    return args


def setup_versioneer(args):
    try:
        pdbv = PDBVersioneer(db_path=args.db_path, config=args.remote_source)
        remote_ver = pdbv.current_remote_version
        return pdbv, remote_ver
    except (socket.timeout, ftplib.error_temp, socket.gaierror):
        logger.error('Could not connect to the FTP server. Please check the URL details and connectivity:')
        url = args.remote_source['url']
        logger.error(f'ftp://{url}')
        sys.exit(1)
    except ValueError:
        logger.error('No valid PDB data found in the remote source. Please check the URL details and connectivity:')
        url = args.remote_source['url']
        logger.error(f'ftp://{url}')
        sys.exit(1)


def download(args, mode='', clean=True, update=False, pdbv=None):
    args.pdbd.remove_unsuccessful = clean
    args.pdbd.set_lock()
    if mode == 'files':
        with clean_exit(callback=args.pdbd.clean_unsuccessful):
            file_types = ['entries', 'entries_type', 'bundles', 'resolution', 'seqres', 'added', 'modified', 'obsolete']
            for file_type in tqdm(file_types, unit='item'):
                result = args.pdbd.download(file_type=file_type)
                if not result:
                    logger.error(f'Failed to download file_type: \"{file_type}\"')
                    sys.exit(1)
            print()
            logger.info('Syncing versioning information...')
            args.pdbd.fetch_version_info()
    elif mode == 'rsync_pdb':
        with clean_exit(callback=args.pdbd.clean_unsuccessful):
            print()
            logger.info('Syncing protein structures in the \'pdb\' format...')
            result = args.pdbd.rsync_pdb_mirror(format='pdb', update=update)
            if result != 0:
                logger.error('Failed to RSYNC with the PDB server')
                sys.exit(1)
    elif mode == 'rsync_cif':
        with clean_exit(callback=args.pdbd.clean_unsuccessful):
            print()
            logger.info('Syncing protein structures in the \'mmCIF\' format...')
            result = args.pdbd.rsync_pdb_mirror(format='mmCIF', update=update)
            if result != 0:
                logger.error('Failed to RSYNC with the PDB server')
                sys.exit(1)
    elif mode == 'adjust_from_config':
        with clean_exit(callback=args.pdbd.clean_unsuccessful):
            root = f'{args.db_path}/data/{pdbv.current_local_version}'
            rest_log = f'{root}/pdb_version_info.json'
            rest_entries = f'{root}/pdb_entries_type.txt'
            curr_log = f'{root}/.versioning.log'

            print()
            logger.info('Syncing additional versioning information to restore from config...')
            args.pdbd.fetch_version_info(out_fn=curr_log, entries_fn=rest_entries)

            with open(rest_log) as f:
                rest_dict = json.loads(f.read())
            with open(curr_log) as f:
                curr_dict = json.loads(f.read())
            modified_entries = {pdb: (ver, True if curr_dict.get(pdb, True) is True else False) for pdb, ver in
                                rest_dict.items() if
                                rest_dict[pdb].split('.')[0] != curr_dict.get(pdb, '0.0').split('.')[0]}

            print()
            logger.info('Adjusting structure mirror to correctly restore from config...')
            result = args.pdbd.download_pdb_versioned(modified_entries)
            print()
            if not result:
                logger.error('Failed to adjust structure mirror!')
                sys.exit(1)
    args.pdbd.remove_lock()


def install_plugins(args):
    pdbv, args.remote_version = setup_versioneer(args)
    config = Config(args.db_path / 'config.yml')
    print()
    if args.update: # In case of an update use a list of installed plugins from config
        if len((config.data['plugins'])) > 0:
            logger.info(f'Updating plugins...')
            args.plugins = config.data['plugins']
    else:
        if args.plugins:
            plugins = set(args.plugins) - set(config.data['plugins'])
            installed_plugins = set(config.data['plugins']) & set(args.plugins)
            if len(plugins) != len(args.plugins):
                installed_plugins_str = ', '.join(list(installed_plugins))
                logger.warning(f'Plugin(s): {installed_plugins_str} were already installed, use the \'--update\' option to sync them.')
            args.plugins = plugins
    for plugin in args.plugins:
        print()
        if args.update:
            logger.info(f'Updating plugin: \'{plugin}\'...')
        else:
            logger.info(f'Setting up plugin: \'{plugin}\'...')

        Plugin = getattr(importlib.import_module('localpdb.plugins.{}'.format(plugin)), plugin)
        plugin_dir = args.db_path / Plugin.plugin_dir  # Absolute directory where plugins are stored
        plv = PluginVersioneer(plugin_dir) # Plugin versioneer
        lpdb_versions = set(pdbv.local_pdb_versions)

        if not Plugin.plugin_config['available_historical_versions'] and len(
                lpdb_versions - plv.installed_plugin_versions) > 0:
            logger.warning(f'Plugin \'{plugin}\' does not support the history versioning. Only version corresponding to the current PDB release can be installed.')
            lpdb_versions = lpdb_versions & {pdbv.current_remote_version}

        # Handle plugins requiring PDB files copy
        if Plugin.plugin_config['requires_pdb']:
            if not config.data['struct_mirror']['pdb']:
                logger.error(f'Plugin \'{plugin}\' requires a local copy of structure files in the PDB format. Run \'localpdb_setup --fetch_pdb\' first.')
                lpdb_versions = set()
            else:
                if not config.data['struct_mirror']['pdb_init_ver'] == config.data['init_ver']:
                    versions_wo_struct = {ver for ver in pdbv.local_pdb_versions if
                                          ver < config.data['struct_mirror']['pdb_init_ver']}
                    if len(versions_wo_struct) > 0:
                        versions_wo_struct_str = ', '.join(sorted([str(ver) for ver in versions_wo_struct]))
                        logger.warning(f'Plugin \'{plugin}\' cannot be installed for version(s): {versions_wo_struct_str}, because structures (PDB format) were synced in the version \'{pdbv.first_local_version}\'.')
                        lpdb_versions = lpdb_versions - versions_wo_struct

        # Handle plugins requiring mmCIF files copy
        if Plugin.plugin_config['requires_cif']:
            if not config.data['struct_mirror']['cif']:
                logger.error(f'Plugin \'{plugin}\' requires a local copy of structure files in the mmCIF format. Run \'localpdb_setup --fetch_cif\' first.')
                lpdb_versions = set()
            else:
                if not config.data['struct_mirror']['cif_init_ver'] == config.data['init_ver']:
                    versions_wo_struct = {ver for ver in pdbv.local_pdb_versions if
                                          ver < config.data['struct_mirror']['cif_init_ver']}
                    if len(versions_wo_struct) > 0:
                        versions_wo_struct_str = ', '.join(sorted([str(ver) for ver in versions_wo_struct]))
                        logger.warning(f'Plugin \'{plugin}\' cannot be installed for version(s): {versions_wo_struct_str}, because structures (mmCIF format) were synced in the version \'{pdbv.first_local_version}\'.')
                        lpdb_versions = lpdb_versions - versions_wo_struct

        # Iterate only over the lpdb versions that the plugin wasn't already setup for.
        lpdb_versions = lpdb_versions - plv.installed_plugin_versions

        if len(lpdb_versions) == 0:
            logger.info(f'Plugin \'{plugin}\' is set up for all currently possible localpdb versions.')
        else:
            lpdb_versions = sorted(list(lpdb_versions))  # Sort to go from oldest to newest
            ver_string = ' '.join([str(ver) for ver in lpdb_versions])
            logger.info(f'Attempting to install plugin \'{plugin}\' for localpdb version(s): {ver_string}')
            for lpdb_version in lpdb_versions:
                lpdb = PDB(args.db_path, version=lpdb_version)
                pl = Plugin(lpdb)
                try:
                    pl.setup() if int(lpdb_version) == pdbv.first_local_version else pl.update()
                    logger.info(f'Successfully installed plugin \'{plugin}\' for the localpdb version: {lpdb_version}')
                    if not args.update:
                        config.data['plugins'].append(plugin)
                        config.commit()
                except PluginAlreadyInstalledOutdated:
                    logger.info(f'Plugin \'{plugin}\' is already installed for the localpdb version \'{lpdb_version}\' but the version is outdated.')
                except PluginInstallError:
                    logger.info(f'Could not set up plugin \'{plugin}\' for the localpdb version \'{lpdb_version}\'')
        print()


def main():

    # Get commandline arguments
    args = get_params()


    # Load config
    args.remote_source = load_remote_source(args.mirror)

    # Override config options if custom urls were provided
    if args.ftp_url:
        args.remote_source['url'] = args.ftp_url
    if args.rsync_url:
        args.remote_source['rsync_url'] = args.rsync_url
    if args.rsync_opts:
        args.remote_source['rsync_opts'] = args.rsync_opts
    if args.download_proto:
        args.remote_source['download_proto'] = args.download_proto

    pdbv, args.remote_version = setup_versioneer(args)
    args.pdbd = PDBDownloader(db_path=args.db_path, version=args.remote_version, config=args.remote_source)

    # Check if directory already exists - won't ask this question if run is restarted because of cancelling / failure
    if os.path.exists(args.db_path) and os.path.isdir(args.db_path) and not pdbv.check_init():
        if len(os.listdir(args.db_path)):
            logger.warning(f'Specified directory \'{args.db_path}\' exists and is not empty!')
    else:
        create_directory(args.db_path)

    if pdbv.current_local_version is not None and args.from_config:
        logger.error(f'Cannot setup localpdb with the \'from_config\' option in the different localpdb directory!')
        sys.exit(1)

    # localpdb is not set up - start from scratch
    if pdbv.current_local_version is None:
        if args.update:
            logger.error(f'localpdb is not set up in the directory: \'{args.db_path}\'!')
            sys.exit(1)
        if args.from_config:
            print()
            print(f'This script will setup the localpdb database in the directory:\n{args.db_path}. '\
                  f'\n\nRestoring from the config specified in:\n{args.from_config}')
            with tarfile.open(args.from_config) as arch:
                arch.extractall(args.db_path)
            # Create directories
            dirs = ['mirror', 'mirror/pdb', 'mirror/mmCIF', 'logs']
            for _dir in dirs:
                create_directory('{}/{}'.format(args.db_path, _dir))
            pdbv.init()
        else:
            print()
            print(f'This script will setup the localpdb database in the directory:\n{args.db_path}')
            print()
            # Create directories
            dirs = ['data', 'mirror', 'mirror/pdb', 'mirror/mmCIF', 'logs', f'data/{args.remote_version}']
            for _dir in dirs:
                create_directory('{}/{}'.format(args.db_path, _dir))
            pdbv.init()

            # Download PDB files
            logger.debug(f'Using \'{args.mirror}\' mirror for downloads.')
            logger.debug(f'Current remote PDB version is \'{args.remote_version}\'')
            logger.info(f'Downloading release data for the PDB version: \'{args.remote_version}\'...')

            download(args, mode='files')

        config = Config(args.db_path / 'config.yml', init=True)
        conf_dict = {'init_ver': args.remote_version, 'struct_mirror': {'pdb': False, 'pdb_init_ver': None,
                                                                        'cif': False, 'cif_init_ver': None},
                     'plugins': []}
        if args.from_config:
            pdbv, args.remote_version = setup_versioneer(args) # Reinitialize versioneer to catch the extracted version
            conf_dict['init_ver'] = pdbv.current_local_version
            pdbv.update_logs(first=True, version=pdbv.current_local_version)
        else:
            pdbv.update_logs(first=True)
        config.data = conf_dict
        config.commit()
        print()
        logger.info(f'Successfully set up localpdb in \'{args.db_path}\'')

        # RSYNC PDB structures
        if any((args.fetch_pdb, args.fetch_cif)):
            print()
            logger.info(f'Downloading protein structures...')
            logger.warning('This can take around 1 to 3 hours depending on your internet connection and requires around ' \
                           '50 GB of disk space for each format file that will be synced.')
            logger.warning('If the run will be stopped it can be restarted later.')
            #TODO Download size warning
            if args.fetch_pdb:
                download(args, mode='rsync_pdb', clean=False)
                conf_dict['struct_mirror'].update(
                    {'pdb': args.fetch_pdb, 'pdb_init_ver': args.remote_version if args.fetch_pdb else None})
                config.commit()
                logger.info(f'Successfully synced protein structures in the \'pdb\' format!')
            if args.fetch_cif:
                if args.from_config:
                    args.pdbd.version = pdbv.current_local_version
                    download(args, mode='rsync_cif', clean=False)
                    download(args, mode='adjust_from_config', clean=True, pdbv=pdbv)
                else:
                    download(args, mode='rsync_cif', clean=False)
                conf_dict['struct_mirror'].update({'cif': args.fetch_cif,
                                                   'cif_init_ver': pdbv.current_local_version if args.fetch_cif and args.from_config
                                                   else args.remote_version if args.fetch_cif else None})
                config.commit()
                logger.info(f'Successfully synced protein structures in the \'mmCIF\' format!')

    # localpdb is set up and up to date
    elif args.remote_version == pdbv.current_local_version:
        config = Config(args.db_path / 'config.yml')
        # check if structure sync is requested on the already set up localpdb

        if not config.data['struct_mirror']['pdb'] and args.fetch_pdb and not args.update:
            download(args, mode='rsync_pdb', clean=False)
            logger.info(f'Successfully synced protein structures in the \'pdb\' format!')
            print()
            config.data['struct_mirror']['pdb'] = True
            config.data['struct_mirror']['pdb_init_ver'] = args.remote_version
        if not config.data['struct_mirror']['cif'] and args.fetch_cif and not args.update:
            download(args, mode='rsync_cif', clean=False)
            logger.info(f'Successfully synced protein structures in the \'mmCIF\' format!')
            print()
            config.data['struct_mirror']['cif'] = True
            config.data['struct_mirror']['cif_init_ver'] = args.remote_version

        else:
            print()
            logger.info(f'localpdb is up to date and set up in the directory \'{args.db_path}\'.')
        config.commit()

    # localpdb is set up but there's a newer remote version available
    elif args.remote_version > pdbv.current_local_version:
        if args.update:
            print()
            logger.info(
                'localpdb is {} update(s) behind with the remote source, updating to version {}...'.format(
                    len(pdbv.missing_remote_versions), pdbv.current_remote_version))
            print()
            config = Config(args.db_path / 'config.yml').data
            # Create directories
            dirs = ['data', 'mirror', 'mirror/pdb', 'mirror/mmCIF', 'logs', f'data/{args.remote_version}']
            for _dir in dirs:
                create_directory('{}/{}'.format(args.db_path, _dir))

            # Download PDB files
            logger.debug(f'Using \'{args.mirror}\' mirror for downloads.')
            if len(pdbv.missing_remote_versions) > 1:
                args.remote_version = pdbv.missing_remote_versions
                args.pdbd = PDBDownloader(db_path=args.db_path, version=args.remote_version, config=args.remote_source)
            download(args, mode='files')
            if not any([config['struct_mirror']['pdb'], config['struct_mirror']['cif']]):
                logger.debug('Skipping structure files syncing...')
            if config['struct_mirror']['pdb']:
                download(args, mode='rsync_pdb', clean=True, update=True)
            if config['struct_mirror']['cif']:
                download(args, mode='rsync_cif', clean=True, update=True)
            pdbv.update_logs()
            print()
            logger.info(
                f'Successfully updated localpdb in \'{args.db_path}\' to version \'{pdbv.current_remote_version}\'!')
        else:
            logger.info(
                f'localpdb is set up in the directory \'{args.db_path}\' but is not up to date. Consider an update!')
            if any([args.fetch_pdb, args.fetch_cif]):
                logger.warning('Structure files cannot be synced when local version is outdated. Update localpdb first.')
    install_plugins(args)
    # Move log file to localpdb dir
    logging.shutdown()
    log_path = args.db_path / 'logs'
    shutil.move(fn_log, log_path)


if __name__ == "__main__":
    main()
