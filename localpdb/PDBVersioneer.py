import os
import ftplib
import logging
import json
import datetime
import warnings
from pathlib import Path
from urllib.parse import urlparse
from localpdb.utils.os import create_directory, custom_warning
logger = logging.getLogger(__name__)

warnings.showwarning = custom_warning


class PDBVersioneer:

    def __init__(self, db_path, config=None):
        self.config = config
        self.db_path = Path(db_path)
        # Check local versions (read log)
        try:
            with open('{}/data/status.log'.format(self.db_path)) as f: #TODO
                data = json.loads(f.read())
                local_versions = [int(key) for key, value in data.items() if value[0] == 'OK']
        except FileNotFoundError:
            # Check local versions (list directories)
            try:
                local_versions = sorted([int(ver) for ver in os.listdir(f'{self.db_path}/data/') if ver.isalnum() and len(ver) == 8])
            except FileNotFoundError:
                local_versions = []
        self.local_pdb_versions = sorted(local_versions)

    def update_logs(self, first=False, version=None):
        ver = self.current_remote_version if version is None else version
        logs_fn = f'{self.db_path}/data/status.log'
        status = ['OK', datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
        if first:
            logs = {ver: status}
        else:
            with open(logs_fn) as f:
                logs = json.loads(f.read())
            logs[ver] = status
        with open(logs_fn, 'w') as f:
            f.write(json.dumps(logs, indent=4))

    def adjust_pdb_ids(self, id_dict, version, mode='load'):
        """
        @param id_dict: Entries - dict {id: id} format
        @param version: localpdb version to check
        @param mode: Either 'load' or 'setup'
        @returns Modified entries dict {id: adjusted_id)
        """
        curr_ids = set(id_dict.keys())
        log_fn = f'{self.db_path}/data/versioning.log'
        change_dict = {}
        try:
            with open(log_fn) as f:
                history = json.loads(f.read())
        except FileNotFoundError:
            history = {}
        for key, h in history.items():
            if mode == 'setup':
                vers = [ver for ver in h if ver <= version]
            else:
                vers = [ver for ver in h if ver > version]
            if len(vers) > 0 and key in curr_ids:
                if mode == 'setup':
                    id_dict[key] = f'{key}_b{max(vers)}'
                    change_dict[key] = f'{key}_b{max(vers)}'
                else:
                    id_dict[key] = f'{key}_b{min(vers)}'
                    change_dict[key] = f'{key}_b{min(vers)}'
        return id_dict, change_dict

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
        p = urlparse('ftp://' + self.config['url'])
        ftp = ftplib.FTP(p.netloc, timeout=10)
        ftp.login("anonymous", "")
        raw_data = []
        ftp.dir(f'{p.path}/data/status/', raw_data.append)
        remote_pdb_versions = sorted([int(entry.split(' ')[-1]) for entry in raw_data if entry.split(' ')[-1].isnumeric()])
        if len(remote_pdb_versions) == 0:
            raise ValueError('No valid PDB versions found in the remote source!')
        return remote_pdb_versions
