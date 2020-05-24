#! /usr/bin/env python3
import os
import argparse
import logging
import sys
import shutil
import socket
from tqdm import tqdm
from pathlib import Path
from localpdb import PDBVersioneer, PDBDownloader
from localpdb.utils.os import create_directory, setup_logging_handlers, clean_exit
from localpdb.utils.config import load_remote_source, Config

# Parse arguments
parser = argparse.ArgumentParser(description='localpdb setup script')
parser.add_argument('-db_path', help='Path to store localpdb database', required=True, metavar='DB_PATH')
parser.add_argument('-mirror', help='''PDB mirror used to download the protein structures. 
Valid options are \'rcsb\' (RCSB PDB - US), \'pdbe\' (PDBe - UK) or \'pdbj\' (PDBj - Japan)''',
                    default='rcsb', metavar='MIRROR')

# Add optional arguments to manually define PDB mirror (these options override the mirror definition from -mirror)
# Used mostly for testing purposes.
parser.add_argument('-tmp_path', help=argparse.SUPPRESS, default='/tmp/')
parser.add_argument('-ftp_url', help=argparse.SUPPRESS)
parser.add_argument('-rsync_url', help=argparse.SUPPRESS)
parser.add_argument('-rsync_opts', help=argparse.SUPPRESS)
parser.add_argument('-clust_url', help=argparse.SUPPRESS)
args = parser.parse_args()
args.db_path = Path(os.path.abspath(args.db_path))

# Setup logging
fn_log, handlers = setup_logging_handlers(tmp_path=args.tmp_path)
logging.basicConfig(level=logging.DEBUG, handlers=handlers, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Validate mirrors
if args.mirror not in ['rcsb', 'pdbe', 'pdbj']:
    logger.error('Wrong PDB mirror server specified! Valid options are: ' 
                 '\'rcsb\' (RCSB PDB - US), \'pdbe\' (PDBe - UK) or \'pdbj\' (PDBj - Japan)')
    sys.exit(1)

# Load config
remote_source = load_remote_source(args.mirror)

# Override config options if custom urls were provided
if args.ftp_url:
    remote_source['ftp_url'] = args.ftp_url
if args.rsync_url:
    remote_source['rsync_url'] = args.rsync_url
if args.rsync_opts:
    remote_source['rsync_opts'] = args.rsync_opts
if args.clust_url:
    remote_source['clust_url'] = args.clust_url

print()
print(f'This script will update the localpdb database in the directory:\n{args.db_path}')
print()

try:
    pdbv = PDBVersioneer(db_path=args.db_path, config=remote_source)
    current_remote_version = pdbv.current_remote_version
except socket.timeout:
    logger.error('Could not connect to the FTP server. Please check the URL details:')
    url = remote_source['ftp_url']
    logger.error(f'ftp://{url}')
    sys.exit(1)
except ValueError:
    logger.error('No valid PDB data found in the remote source. Please check the URL details:')
    url = remote_source['ftp_url']
    logger.error(f'ftp://{url}')
    sys.exit(1)

if pdbv.current_local_version is None:
    logger.error(f'localpdb is not set up directory \'{args.db_path}\'')
    sys.exit(1)

elif current_remote_version == pdbv.current_local_version:
    logger.info(f'localpdb is up to date and set up in the directory \'{args.db_path}\'.')

elif current_remote_version > pdbv.current_local_version:

    config = Config(db_path=args.db_path)

    n_missing_versions = len(pdbv.missing_remote_versions)
    if n_missing_versions == 1:
        logger.info(f'localpdb is {n_missing_versions} update behind with the remote source, updating...')
        pdbd = PDBDownloader(db_path=args.db_path, version=current_remote_version, config=remote_source)
    else:
        logger.info(f'localpdb is {n_missing_versions} updates behind with the remote source, updating...')
        pdbd = PDBDownloader(db_path=args.db_path, version=pdbv.missing_remote_versions, config=remote_source)
    print()

    # Create directories
    dirs = [f'data/{current_remote_version}', f'clustering/{current_remote_version}']
    for _dir in dirs:
        create_directory('{}/{}'.format(args.db_path, _dir))

    # Download PDB files
    logger.debug(f'Using \'{args.mirror}\' mirror for downloads.')
    logger.debug(f'Current remote PDB version is \'{current_remote_version}\'')
    logger.info(f'Downloading release data for the PDB version: \'{current_remote_version}\'...')
    pdbd.set_lock()

    # Run the downloads in the 'exit' context to eventually clean partially downloaded files if whole run does not succeed
    with clean_exit(callback=pdbd.clean_unsuccessful):
        clust_types = [f'clust_{p}' for p in [30, 40, 50, 70, 90, 95, 100]]
        file_types = ['entries', 'entries_type', 'bundles', 'resolution', 'seqres', 'updates'] + clust_types
        for file_type in tqdm(file_types, unit='item'):
            result = pdbd.download(file_type=file_type)
            if not result:
                logger.error(f'Failed to download file_type: \"{file_type}\"')
                sys.exit(1)
        print()

        # RSYNC PDB structures
        if any((config.data['mirror_pdb'], config.data['mirror_cif'])):
            logger.info(f'Downloading protein structures...')
            logger.info('(If the run will be stopped it can be restarted later.)')
            print()
            if config.data['mirror_pdb']:
                logger.info('Syncing protein structures in the \'pdb\' format...')
                result = pdbd.rsync_pdb_mirror(format='pdb')
                print()
                if result != 0:
                    logger.error('Failed to RSYNC with the PDB server')
                    sys.exit(1)
            if config.data['mirror_cif']:
                logger.info('Syncing protein structures in the \'mmCIF\' format...')
                result = pdbd.rsync_pdb_mirror(format='mmCIF')
                print()
                if result != 0:
                    logger.error('Failed to RSYNC with the PDB server')
                    sys.exit(1)

        pdbd.remove_lock()
        # Finally - setup log and report success
        pdbv.update_logs()
        print()
        logger.info(f'Successfully updated localpdb in \'{args.db_path}\' to version \'{current_remote_version}\'!')
        # Move log file to localpdb dir
        logging.shutdown()
        log_path = args.db_path / 'logs'
        shutil.move(fn_log, log_path)
