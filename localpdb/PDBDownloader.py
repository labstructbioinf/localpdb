import logging
import os
import datetime
import sys
import shutil
import json
import requests
import numpy as np
from pathlib import Path
from tqdm import tqdm
from .PDBVersioneer import PDBVersioneer
from localpdb.utils.os import set_last_modified, os_cmd, parse_simple
from localpdb.utils.network import get_last_modified, download_url

logger = logging.getLogger(__name__)


class PDBDownloader:
    """
    Class for handling downloads from the PDB servers.
    """

    def __init__(self, db_path, version, config, remove_unsuccessful=False):
        """
        @param db_path: localpdb database path
        @param version: PDB version or versions (if in update mode with multiple missing versions)
        @param mirror: PDB mirror to download from
        @param config: Config dict with remote source information
        @param remove_unsuccessful: Remove downloaded files in case of download failure (True/False)
        """
        self.config = config
        self.db_path = Path(db_path)
        self.remove_unsuccessful = remove_unsuccessful
        self.versions = None
        self.pdbv = PDBVersioneer(db_path, config=config)
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
        try:
            shutil.copy(f'{self.db_path}/data/versioning.log', f'{self.db_path}/data/.versioning.log.bk')
        except FileNotFoundError:
            pass
        self.cp_files = []

    def __gen__url(self, file_type='', version=None):
        """
        Generates download url for given file type based on the selected PDB mirror defined in the config file
        @param file_type: file type
        @return: url to download the file
        """
        root = self.config['url']
        proto = self.config['download_proto']
        if file_type in ['entries', 'entries_type', 'bundles', 'resolution', 'seqres']:
            ext = self.config['ftp_locs'][file_type]
            url = f'{proto}://{root}/{ext}'
        elif file_type in ['added', 'modified', 'obsolete']:
            ext = self.config['ftp_locs'][file_type]
            if version is None:
                raise ValueError('PDB version needs to be specified!')
            url = f'{proto}://{root}/{ext}/{version}/{file_type}.pdb'
        else:
            raise ValueError('Unknown file type, cannot generate download url!')
        return url

    def __gen_url_versioned_pdb(self, pdb_id, version, obsolete=False):
        major, minor = version.split('.')
        root = self.config['versioned_url']
        proto = self.config['download_proto']
        if obsolete:
            minor = str(int(minor)+1)
            url = f'{proto}://{root}/data/removed/{pdb_id[1:3]}/pdb_0000{pdb_id}/pdb_0000{pdb_id}_xyz_v{major}-{minor}.cif.gz'
        else:
            url = f'{proto}://{root}/views/all/coordinates/mmcif/{pdb_id[1:3]}/pdb_0000{pdb_id}/pdb_0000{pdb_id}_xyz_v{major}.cif.gz'
        return url

    def __verify_timestamp(self, fn, version=None, lazy=False):
        """
        Verifies the timestamp of the downloaded file against the PDB version.
        @param fn: filename of the file
        @param version: PDB version
        @return: True if timestamp matches the version, else False
        """
        if lazy:
            return True
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
            dest = f'{self.db_path}/data/{self.version}/pdb_{file_type}.txt'
            if file_type == 'seqres':
                dest = '{}.gz'.format(dest)
            url = self.__gen__url(file_type=file_type)
            if download_url(url, dest):
                if file_type == 'bundles':
                    return True
                else:
                    return self.__verify_timestamp(dest)
            else:
                return False

        elif file_type in ['added', 'modified', 'obsolete']:
            url = self.__gen__url(file_type=file_type, version=self.version)
            dest = f'{self.db_path}/data/{self.version}/{file_type}.txt'
            results = [self.__verify_timestamp(dest, lazy = True if file_type=='obsolete' else False) if download_url(url, dest) else False]

            if file_type == 'modified':
                modified_dict, status = self.fetch_major_revisions()
                results.append(status)
            if self.versions is not None:
                dest_merged = f'{self.db_path}/data/{self.version}/{file_type}_merged.txt'
                with open(dest_merged, 'w') as f:
                    for version in self.versions:
                        tmp_dest = f'{self.db_path}/data/{self.version}/tmp_{version}_{file_type}.txt'
                        url = self.__gen__url(file_type=file_type, version=version)
                        if download_url(url, tmp_dest):
                            if file_type != 'obsolete':
                                results.append(self.__verify_timestamp(tmp_dest, version=version))
                            else:
                                results.append(True)
                            with open(tmp_dest) as f_tmp:
                                f.write(f_tmp.read())
                            os.remove(tmp_dest)
                        else:
                            results.append(False)
                last_modified = get_last_modified(url)
                set_last_modified(dest_merged, last_modified)
                if file_type == 'modified':
                    modified_dict, status = self.fetch_major_revisions(merged=True)
                    results.append(status)
            if all(results) and file_type == 'modified':
                results.append(self.update_versioning_log(modified_dict))
            return all(results)

    def download_pdb_versioned(self, entries):
        """
        @param entries: Dictionary with pdb_id and version id as keys and values.
        """
        results = []
        for pdb_id, (version, obsolete) in tqdm(entries.items()):
            url = self.__gen_url_versioned_pdb(pdb_id, version, obsolete=obsolete)
            dest = f'{self.db_path}/mirror/mmCIF//{pdb_id[1:3]}/{pdb_id}.cif.gz'
            result = download_url(url, dest)
            results.append(result)
        return all(results)

    def fetch_major_revisions(self, merged=False):
        """
        Check with RCSB graphql API for major revisions (i.e. the coordinate changes) for modified entries downloaded
        by the self.download() function.
        @param merged: Denotes whether modified entries are a weekly RCSB update or merged updates over multiple versions.
        @return: True if check succeeded, False otherwise
        """
        in_fn = f'{self.db_path}/data/{self.version}/modified_merged.txt' \
            if merged else f'{self.db_path}/data/{self.version}/modified.txt'
        out_fn = f'{self.db_path}/data/{self.version}/modified_major_merged.txt' \
            if merged else f'{self.db_path}/data/{self.version}/modified_major.txt'
        with open(in_fn) as f:
            entries = {line.rstrip() for line in f}
        try:
            modified_dict = query_major_revisions(entries, self.versions[0], self.versions[-1]) \
                if merged else query_major_revisions(entries, self.version, self.version)
        except requests.exceptions.RequestException:
            return {}, False
        with open(out_fn, 'w') as f:
            for id_ in modified_dict.keys():
                f.write(f'{id_}\n')
        return modified_dict, True

    def update_versioning_log(self, modified_dict):
        """
        Updates the versioning.log file that keeps the major modifications of PDB entries.
        @param modified_dict: Revision data (dictionary from the self.fetch_major_revisions)
        @return: True if update succeeded, False otherwise
        """
        logs_fn = f'{self.db_path}/data/versioning.log'
        try:
            with open(logs_fn) as f:
                ver_history = json.loads(f.read())
            for pdb_id, rev_ver in modified_dict.items():
                if pdb_id in ver_history.keys():
                    ver_history[pdb_id].append(rev_ver)
                else:
                    ver_history[pdb_id] = [rev_ver]
        except FileNotFoundError:
            ver_history = {}
        with open(logs_fn, 'w') as f:
            f.write(json.dumps(ver_history, indent=4))
        return True

    def rsync_pdb_mirror(self, format='pdb', update=False):
        """
        Handles the RSYNC session with the PDB servers to download files in the selected format
        @param format: file format to download ('pdb' or 'mmCIF')
        @param update: denotes whether rsync will be in the update mode
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
        rsync_dry_cmd = f'rsync -nrlpt -v {add_opts} {url}/{format}/ {local_mirror}/'
        result, (stdout, _) = os_cmd(rsync_dry_cmd)
        n_structs = len([line for line in stdout])
        if update:
            n_structs += 2
        if result != 0:
            return 1

        fn_modified = f'{self.db_path}/data/{self.version}/modified_major.txt' if self.versions is None \
            else f'{self.db_path}/data/{self.version}/modified_major_merged.txt'
        modified = parse_simple(fn_modified)
        fn_obsolete = f'{self.db_path}/data/{self.version}/obsolete.txt' if self.versions is None \
            else f'{self.db_path}/data/{self.version}/obsolete_merged.txt'
        obsolete = parse_simple(fn_obsolete)
        bundles = parse_simple(f'{self.db_path}/data/{self.version}/pdb_bundles.txt')

        ids = list(modified-bundles-obsolete) if format == 'pdb' else list(modified-obsolete)
        _, map_dict = self.pdbv.adjust_pdb_ids({id_: id_ for id_ in ids}, self.version, mode='setup')
        if len(map_dict) > 0:
            logger.info(f'INFO: {len(map_dict)} entries in the {format} format had major coordinate revision without PDB id changes. '
                        f'Accounting for this during the mirror update.')
        for pdb_id in map_dict.keys():
            if format == 'pdb':
                org_fn = f'{self.db_path}/mirror/pdb/{pdb_id[1:3]}/pdb{pdb_id}.ent.gz'
                dest_fn = f'{self.db_path}/mirror/pdb/{pdb_id[1:3]}/pdb{map_dict[pdb_id]}.ent.gz'
            else:
                org_fn = f'{self.db_path}/mirror/mmCIF/{pdb_id[1:3]}/{pdb_id}.cif.gz'
                dest_fn = f'{self.db_path}/mirror/mmCIF/{pdb_id[1:3]}/{map_dict[pdb_id]}.cif.gz'
            try:
                shutil.copy2(org_fn, dest_fn)
                self.cp_files.append((org_fn, dest_fn))
                logger.debug(f'Moved file\'{org_fn}\' to \'{dest_fn}\'.')
            except:
                logger.debug(f'File \'{org_fn}\' that was supposed to be moved (versioning) does not exist.')

        # Now run main rsync process with the tqdm progress bar
        tqdm_str = f'tqdm --unit_scale --unit=item --dynamic_ncols=True --total={n_structs} >> /dev/null '
        rsync_cmd = f'rsync -rlpt -v {add_opts} {url}/{format}/ {local_mirror}/ | {tqdm_str}'
        result = os.system(rsync_cmd)
        return result

    def fetch_version_info(self, out_fn=None, entries_fn=None):
        if entries_fn is None:
            entries_fn = f'{self.db_path}/data/{self.version}/pdb_entries_type.txt'
        if out_fn is None:
            out_fn = f'{self.db_path}/data/{self.version}/pdb_version_info.json'
        with open(entries_fn) as f:
            entries = [line.split('\t')[0] for line in f.readlines()]
        version_info = {}
        for batch in tqdm(np.array_split(entries, 100)):
            version_info.update(query_versions(batch))
        with open(out_fn, 'w') as f:
            f.write(json.dumps(version_info, indent=4))

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
        if self.remove_unsuccessful:
            rm_strings = [f'{self.db_path}/data/{self.version}', f'{self.db_path}/clustering{self.version}']
            try:
                shutil.move(f'{self.db_path}/data/.versioning.log.bk', f'{self.db_path}/data/versioning.log')
            except FileNotFoundError:
                pass
            for s in rm_strings:
                try:
                    shutil.rmtree(s)
                except FileNotFoundError:
                    pass
            for org_fn, dest_fn in self.cp_files:
                try:
                    shutil.copy2(dest_fn, org_fn)
                    logger.debug(f'Moved file\'{dest_fn}\' to \'{org_fn}\'.')
                    os.remove(dest_fn)
                except FileNotFoundError:
                    pass

        self.remove_lock()


def convert_iso_date(date):
    d = datetime.datetime.strptime(date,"%Y-%m-%dT%H:%M:%SZ")
    timestamp = d - datetime.timedelta(days=5)
    return int(f'{timestamp.year}{str(timestamp.month).zfill(2)}{str(timestamp.day).zfill(2)}')


def query_versions(entries):
    query = """{entries(entry_ids: %s){rcsb_id, pdbx_audit_revision_history {major_revision, minor_revision}}}""" % json.dumps(
        list(entries))
    r = requests.post("https://data.rcsb.org/graphql", json={"query": query}).json()
    data = {entry['rcsb_id'].lower(): '{}.{}'.format(entry['pdbx_audit_revision_history'][-1]['major_revision'],
                                                     entry['pdbx_audit_revision_history'][-1]['minor_revision'])
            for entry in r['data']['entries']}
    return data


def query_major_revisions(entries, min_version=None, max_version=None):
    query = """{entries(entry_ids: %s){rcsb_id, pdbx_audit_revision_history {major_revision, minor_revision, revision_date}}}""" % json.dumps(
        list(entries))
    r = requests.post("https://data.rcsb.org/graphql", json={"query": query}).json()

    data = {entry['rcsb_id'].lower(): [(convert_iso_date(rev_data['revision_date']), rev_data['major_revision'],
                                        rev_data['minor_revision'])
                                       for i, rev_data in enumerate(entry['pdbx_audit_revision_history'])]
            for entry in r['data']['entries']}
    data_filt = {key: [history[i][0] for i in range(1, len(history))
                       if max_version >= history[i][0] >= min_version
                       and history[i][1] != history[i - 1][1]] for key, history in data.items()}
    revisions = {key: value[-1] for key, value in data_filt.items() if len(value) > 0}
    return revisions
