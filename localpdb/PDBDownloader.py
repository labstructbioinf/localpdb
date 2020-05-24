import logging
import os
import datetime
import sys
import shutil
from pathlib import Path
from localpdb.utils.os import set_last_modified, os_cmd
from localpdb.utils.network import get_last_modified, download_url

logger = logging.getLogger(__name__)

class PDBDownloader:
    """
    Class for handling downloads from the PDB servers.
    """

    def __init__(self, db_path, version, config):
        """
        @param db_path: localpdb database path
        @param version: PDB version or versions (if in update mode with multiple missing versions)
        @param mirror: PDB mirror to download from
        """
        self.config = config
        self.db_path = Path(db_path)
        self.versions = None
        if type(version) == list:
            self.version = version[-1]
            self.versions = version
        else:
            self.version = version
        if self.check_lock():
            logger.error('Detected another processes setting/updating localpdb in the same path.')
            logger.error('This can also happen if previous runs have been stopped or have failed.')
            logger.error('You can manually override this error by running:')
            logger.error(f'rm {self.db_path}/.lock')
            sys.exit(1)

    def __gen__url(self, file_type='', version=None):
        """
        Generates download url for given file type based on the selected PDB mirror defined in the config file
        @param file_type: file type
        @return: url to download the file
        """
        root = self.config['ftp_url']
        method = 'ftp'
        if file_type in ['entries', 'entries_type', 'bundles', 'resolution', 'seqres']:
            ext = self.config['ftp_locs'][file_type]
            url = f'{method}://{root}/{ext}'
        elif file_type == 'updates':
            ext = self.config['ftp_locs'][file_type]
            if version is None:
                raise ValueError('PDB version needs to be specified!')
            url = f'{method}://{root}/{ext}/{version}/added.pdb'
        elif file_type.startswith('clust_'):
            redundancy = file_type.split('_')[1]
            root = self.config['clust_url']
            method = 'ftp'
            url = f'{method}://{root}/bc-{redundancy}.out'
            return url
        else:
            raise ValueError('Unknown file type, cannot generate download url!')
        return url

    def __verify_timestamp(self, fn, version=None):
        """
        Verifies the timestamp of the downloaded file against the PDB version.
        @param fn: filename of the file
        @param version: PDB version
        @return: True if timestamp matches the version, else False
        """
        if version is None:
            version = self.version
        timestamp = datetime.datetime.fromtimestamp((os.path.getmtime(fn)))
        timestamp = f'{timestamp.year}{str(timestamp.month).zfill(2)}{str(timestamp.day).zfill(2)}'
        out = timestamp == str(version)
        if out:
            logger.debug(f'Timestamp of the file: \'{fn}\' matches the PDB version: \'{version}\'')
        else:
            logger.debug(f'Timestamp of the downloaded file: \'{fn}\' does not match the PDB version: \'{version}\'')
            logger.error(f'Downloaded file creation timestamp does not match the PDB version \'{version}\'')
            logger.error('This is expected behavior when downloading data within few hours before the PDB weekly update'
                         ' (Wednesday 00:00 UTC) or occasionally when using the \'pdbe\' mirror.')
            logger.error('Please try using different mirror or postpone the installation / update for few hours.')
        return out

    def download(self, file_type=''):
        """
        Downloads the selected file type from the selected PDB mirror based on the generated URL.
        @param file_type: file type to download.
        @return: True if downloaded was completed and validated.
        """
        if file_type in ['entries', 'bundles', 'entries_type', 'resolution', 'seqres']:
            dest = '{}/data/{}/pdb_{}.txt'.format(self.db_path, self.version, file_type) # TODO
            if file_type == 'seqres':
                dest = '{}.gz'.format(dest)
            url = self.__gen__url(file_type=file_type)
            if download_url(url, dest, ftp=True):
                return self.__verify_timestamp(dest)
            else:
                return False

        elif file_type.startswith('clust_'):
            url = self.__gen__url(file_type)
            dest = '{}/clustering/{}/{}.out'.format(self.db_path, self.version, file_type) # TODO
            if download_url(url, dest, ftp=True):
                return self.__verify_timestamp(dest)
            else:
                return False

        elif file_type == 'updates':
            if self.versions is None:
                url = self.__gen__url(file_type=file_type, version=self.version)
                dest = '{}/data/{}/added.txt'.format(self.db_path, self.version) # TODO
                if download_url(url, dest, ftp=True):
                    return self.__verify_timestamp(dest)
                else:
                    return False
            else:
                results = []
                f = open('{}/data/{}/added.txt'.format(self.db_path, self.version), 'w')
                for version in self.versions:
                    tmp_dest = '{}/data/{}/tmp_{}_added.txt'.format(self.db_path, self.version, version) # TODO
                    url = self.__gen__url(file_type=file_type, version=version)
                    download_url(url, tmp_dest, ftp=True)
                    results.append(self.__verify_timestamp(tmp_dest, version=version))
                    f_tmp = open(tmp_dest)
                    f.write(f_tmp.read())
                    f_tmp.close()
                    os.remove(tmp_dest)
                last_modified = get_last_modified(url, ftp=True)
                set_last_modified('{}/data/{}/added.txt'.format(self.db_path, self.version), last_modified) #TODO
                return all(results)

    def rsync_pdb_mirror(self, format='pdb'):
        """
        Handles the RSYNC session with the PDB servers to download files in the selected format
        @param format: file format to download ('pdb' or 'mmCIF')
        @return: exit code from the RSYNC (0 if run completed without errors)
        """

        # Set the urls and paths based on the configs
        url = self.config['rsync_url']
        add_opts = self.config['rsync_opts']
        local_mirror = self.db_path / 'mirror' / format

        if format not in ['pdb', 'mmCIF']:
            raise ValueError(f'Format \'{format}\' is not a valid. Only \'pdb\' and \'mmCIF\' formats are allowed!')

        # First make rsync dry run (-n) to check number of structures to be synced.
        # This also checks connectivity with the selected mirror.
        rsync_dry_cmd = f'rsync -nrlpt -v -z {add_opts} {url}/{format}/ {local_mirror}/'
        result, (stdout, _) = os_cmd(rsync_dry_cmd)
        n_structs = len([line for line in stdout])
        if result != 0:
            return 1

        # Now run main rsync process with the tqdm progress bar
        tqdm_str = f'tqdm --unit_scale --unit=item --dynamic_ncols=True --total={n_structs} >> /dev/null '
        rsync_cmd = f'rsync -rlpt -v {add_opts} {url}/{format}/ {local_mirror}/ | {tqdm_str}'
        result = os.system(rsync_cmd)
        return result

    def set_lock(self):
        """
        Sets the lock (empty filename) to prevent multiple download sessions in one localpdb db path.
        """
        Path(self.db_path / '.lock').touch()

    def check_lock(self):
        """
        Checks whether the lock on the localpdb db path is present.
        @return: True or False for lock presence
        """
        return Path(self.db_path / '.lock').is_file()

    def remove_lock(self):
        """
        Removes the lock allowing for the further download sessions in the db path.
        """
        if self.check_lock():
            Path(self.db_path / '.lock').unlink()

    def clean_unsuccessful(self):
        """
        Cleans the files downloaded during the session.
        This function is run when some part of the download session has failed.
        """
        shutil.rmtree(self.db_path / 'data' / str(self.version))
        shutil.rmtree(self.db_path / 'clustering' / str(self.version))
        self.remove_lock()
