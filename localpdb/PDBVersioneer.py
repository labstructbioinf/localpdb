import os
import ftplib
import logging
import json
import datetime
import warnings
from pathlib import Path
from urllib.parse import urlparse
logger = logging.getLogger(__name__)


class PDBVersioneer:

    def __init__(self, db_path, config=None):
        self.config = config
        self.db_path = Path(db_path)
        # Check local versions (list directories)
        try:
            local_versions_dirs = sorted(
                int(ver) for ver in os.listdir('{}/data/'.format(self.db_path)) if ver.isalnum() and len(ver) == 8)
        except FileNotFoundError:
            local_versions_dirs = []

        # Check local versions (read log)
        try:
            with open('{}/data/status.log'.format(self.db_path)) as f: #TODO
                data = json.loads(f.read())
                local_versions_json = [int(key) for key, value in data.items() if value[0] == 'OK']
        except FileNotFoundError:
            local_versions_json = []

        # Raise warning if there is inconsistency between present directories and log
        # This will happen if setup / update run will be terminated abruptly and cleaning method will not manage to
        # delete the temporary files for the failed run.
        if local_versions_dirs != local_versions_json:
            warn_str = f'''Detected inconsistency between the localpdb versions according to the directory listings and the setup/update log file.
This can be a result of a failed setup / update run or using the localpdb during the setup or update.
If this warning persists inspect the directories in \'{self.db_path}/data\' and \'{self.db_path}/data/status.log\' to find inconsistencies.'''
            warnings.warn(warn_str)
            logger.debug(warn_str)

        self.local_pdb_versions = sorted(local_versions_json)

    def update_logs(self, first=False):
        logs_fn = '{}/data/status.log'.format(self.db_path) # TODO
        status = ['OK', datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
        if first:
            logs = {self.current_remote_version: status}
        else:
            with open(logs_fn) as f:
                logs = json.loads(f.read())
            logs[self.current_remote_version] = status
        with open(logs_fn, 'w') as f:
            f.write(json.dumps(logs, indent=4))

    def init(self):
        """
        Create a ".localpdb" file to mark the directory as localpdb db
        """
        Path(self.db_path / '.localpdb').touch()

    def check_init(self):
        """
        Checks whether the localpdb init file ".localpdb" is present.
        @return: True or False for the init file presence
        """
        return Path(self.db_path / '.localpdb').is_file()

    @property
    def current_local_version(self):
        """
        Checks current (newest) available localpdb version
        @return: (int) - current (newest) localpdb version
        """
        try:
            return self.local_pdb_versions[-1]
        except IndexError:
            return None

    @property
    def first_local_version(self):
        """
        Checks for the first (oldest) available localpdb version
        @return: (int) - first (oldest) localpdb version
        """
        try:
            return self.local_pdb_versions[0]
        except IndexError:
            return None

    @property
    def current_remote_version(self):
        """
        Checks for the current (newest) available remote PDB version
        @return: (int) - current (newest) remote PDB version
        """
        return self.remote_pdb_versions[-1]

    @property
    def missing_remote_versions(self):
        """
        Checks for the missing localpdb version w.r.t the remote source
        @return: list with missing localpdb versions
        """
        return self.remote_pdb_versions[self.remote_pdb_versions.index(self.current_local_version)+1:
                                        self.remote_pdb_versions.index(self.current_remote_version)+1]

    @property
    def remote_pdb_versions(self):
        """
        Checks for the remote PDB versions in the PDB ftp mirror
        @return: sorted list of the remote PDB versions available in the PDB ftp mirror
        """
        p = urlparse('ftp://' + self.config['ftp_url'])
        ftp = ftplib.FTP(p.netloc, timeout=10)
        ftp.login("anonymous", "")
        raw_data = []
        ftp.dir(f'{p.path}/data/status/', raw_data.append)
        remote_pdb_versions = sorted([int(entry.split(' ')[-1]) for entry in raw_data if entry.split(' ')[-1].isnumeric()])
        if len(remote_pdb_versions) == 0:
            raise ValueError('No valid PDB versions found in the remote source!')
        return remote_pdb_versions
