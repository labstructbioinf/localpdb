import yaml
import os
import shlex
import shutil
import subprocess
import pytest
import json
import tempfile
from pathlib import Path
from localpdb.utils.config import Config

my_path = os.path.dirname(os.path.realpath(__file__))
with open('{}/test_config.yml'.format(my_path)) as f:
    config = yaml.safe_load(f)

@pytest.fixture(scope='class', autouse=True)
def tmp_path():
    tmp_path = f'{config["tmp_path"]}/{next(tempfile._get_candidate_names())}'
    os.mkdir(tmp_path)
    yield Path(tmp_path)
    shutil.rmtree(tmp_path)


class TestUpdateBasic:

    @pytest.mark.dependency()
    def test_update_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), capture_output=True)
        assert p.returncode == 0

        update_cmd = f'localpdb_update.py ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200424"]["url"]} ' \
                    f'-clust_url {config["pdb_20200424"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200424"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200424"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(update_cmd), capture_output=True)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is 1 update behind with the remote source' in stdout
        assert 'Successfully updated localpdb' in stdout

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_update_in_already_updated_dir(self, tmp_path):
        update_cmd = f'localpdb_update.py ' \
                     f'-db_path {tmp_path} ' \
                     f'-ftp_url {config["pdb_20200424"]["url"]} ' \
                     f'-clust_url {config["pdb_20200424"]["clust_url"]} ' \
                     f'-rsync_url {config["pdb_20200424"]["rsync_url"]} ' \
                     f'-rsync_opts \'{config["pdb_20200424"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(update_cmd), capture_output=True)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is up to date and set up in the directory' in stdout

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 528

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir)]) == 519

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_setup_log_dir(self, tmp_path):
        assert len(os.listdir(tmp_path / 'logs')) == 2

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_setup_log_contents(self, tmp_path):
        assert os.path.isfile(tmp_path / 'data' / 'status.log')
        with open(tmp_path / 'data' / 'status.log', 'r') as f:
            data = json.load(f)
        assert len(data) == 2
        assert data['20200417'][0] == 'OK'
        assert data['20200424'][0] == 'OK'

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_update_run'])
    def test_second_update(self, tmp_path):
        update_cmd = f'localpdb_update.py ' \
                     f'-db_path {tmp_path} ' \
                     f'-ftp_url {config["pdb_20200501"]["url"]} ' \
                     f'-clust_url {config["pdb_20200501"]["clust_url"]} ' \
                     f'-rsync_url {config["pdb_20200501"]["rsync_url"]} ' \
                     f'-rsync_opts \'{config["pdb_20200501"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(update_cmd), capture_output=True)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is 1 update behind with the remote source' in stdout
        assert 'Successfully updated localpdb' in stdout

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_second_update'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 729

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_second_update'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir)]) == 748

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_second_update'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_second_update'])
    def test_setup_log_dir(self, tmp_path):
        assert len(os.listdir(tmp_path / 'logs')) == 3

    @pytest.mark.dependency(depends=['TestUpdateBasic::test_second_update'])
    def test_setup_log_contents(self, tmp_path):
        assert os.path.isfile(tmp_path / 'data' / 'status.log')
        with open(tmp_path / 'data' / 'status.log', 'r') as f:
            data = json.load(f)
        assert len(data) == 3
        assert data['20200417'][0] == 'OK'
        assert data['20200424'][0] == 'OK'
        assert data['20200501'][0] == 'OK'


class TestUpdateSkipOneVersion:

    @pytest.mark.dependency()
    def test_update_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), capture_output=True)
        assert p.returncode == 0

        update_cmd = f'localpdb_update.py ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200501"]["url"]} ' \
                    f'-clust_url {config["pdb_20200501"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200501"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200501"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(update_cmd), capture_output=True)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is 2 updates behind with the remote source' in stdout
        assert 'Successfully updated localpdb' in stdout

    @pytest.mark.dependency(depends=['TestUpdateSkipOneVersion::test_update_run'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 729

    @pytest.mark.dependency(depends=['TestUpdateSkipOneVersion::test_update_run'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir)]) == 748

    @pytest.mark.dependency(depends=['TestUpdateSkipOneVersion::test_update_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestUpdateSkipOneVersion::test_update_run'])
    def test_setup_log_dir(self, tmp_path):
        assert len(os.listdir(tmp_path / 'logs')) == 2

    @pytest.mark.dependency(depends=['TestUpdateSkipOneVersion::test_update_run'])
    def test_setup_log_contents(self, tmp_path):
        assert os.path.isfile(tmp_path / 'data' / 'status.log')
        with open(tmp_path / 'data' / 'status.log', 'r') as f:
            data = json.load(f)
        assert len(data) == 2
        assert data['20200417'][0] == 'OK'
        assert data['20200501'][0] == 'OK'
