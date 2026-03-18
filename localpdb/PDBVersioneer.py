import os
import ftplib
import logging
import json
import warnings
from datetime import date, datetime, timedelta
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
        status = ['OK', datetime.now().strftime("%Y-%m-%d %H:%M")]
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
    def remote_pdb_versions(self, start="20070425", seed="20260206", include_start=False):
        """
        Return all weekly version strings (YYYYMMDD) from the first date aligned with
        the observed cadence up to ref_date.

        Parameters
        ----------
        ref_date : date | str | None
            End date, inclusive. If None, uses date.today().
        start : str
            Lower bound in YYYYMMDD format.
        seed : str
            Any known valid version date from the real sequence, e.g. '20260206'.
            The whole cadence is inferred from this date with a 7-day step.
        include_start : bool
            If True, prepend `start` even when it is not aligned to the cadence.
            Useful if you want to keep a historical special case like 20070425.

        Returns
        -------
        list[str]
        """
        ref_date = date.today()
        def parse_yyyymmdd(x):
            if isinstance(x, date):
                return x
            return datetime.strptime(x, "%Y%m%d").date()

        start_date = parse_yyyymmdd(start)
        seed_date = parse_yyyymmdd(seed)

        if ref_date is None:
            ref_date = date.today()
        else:
            ref_date = parse_yyyymmdd(ref_date)

        if ref_date < start_date:
            return []

        # First date on the seed-based 7-day cadence that is >= start_date
        offset_from_seed = (start_date - seed_date).days % 7
        days_to_next_aligned = (7 - offset_from_seed) % 7
        first_aligned = start_date + timedelta(days=days_to_next_aligned)

        # Last date on the seed-based 7-day cadence that is <= ref_date
        days_since_seed = (ref_date - seed_date).days % 7
        last_aligned = ref_date - timedelta(days=days_since_seed)

        versions = []

        if include_start:
            versions.append(start_date.strftime("%Y%m%d"))

        current = first_aligned
        while current <= last_aligned:
            value = current.strftime("%Y%m%d")
            if not versions or versions[-1] != value:
                versions.append(value)
            current += timedelta(days=7)

        return [int(version) for version in versions]
