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


class TestSetupBasic:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'Successfully set up localpdb' in stdout

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_in_already_setup_dir(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is up to date and set up in the directory' in stdout

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_in_already_setup_outdated(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200424"]["url"]} ' \
                    f'-clust_url {config["pdb_20200424"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200424"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200424"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'but is not up to date. Consider an update!' in stdout

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 249

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir)]) == 250

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_log_dir(self, tmp_path):
        assert len(os.listdir(tmp_path / 'logs')) == 1

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_log_contents(self, tmp_path):
        assert os.path.isfile(tmp_path / 'data' / 'status.log')
        with open(tmp_path / 'data' / 'status.log', 'r') as f:
            data = json.load(f)
        assert len(data) == 1
        assert data['20200417'][0] == 'OK'

    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert os.path.isfile(tmp_path / 'config.yml')
        config = Config(tmp_path)
        assert 'mirror_pdb' in config.data.keys()
        assert config.data['mirror_pdb'] == True
        assert 'mirror_cif' in config.data.keys()
        assert config.data['mirror_cif'] == True


class TestSetupWrongBaseUrl:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"][1:]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'Could not connect to the FTP server.' in stdout

    @pytest.mark.dependency(depends=['TestSetupWrongBaseUrl::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestSetupWrongBaseUrl::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupWrongBaseDir:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"][:-2]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'No valid PDB data found in the remote source.' in stdout

    @pytest.mark.dependency(depends=['TestSetupWrongBaseDir::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestSetupWrongBaseDir::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupWrongTimestamp:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200424"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'Downloaded file creation timestamp does not match the PDB version' in stdout

    @pytest.mark.dependency(depends=['TestSetupWrongTimestamp::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestSetupWrongTimestamp::test_setup_run'])
    def test_setup_fail_cleanup(self, tmp_path):
        assert len(os.listdir(tmp_path / 'data')) == 0
        assert len(os.listdir(tmp_path / 'clustering')) == 0

    @pytest.mark.dependency(depends=['TestSetupWrongTimestamp::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupWrongRsyncUrl:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                    f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                    f'-rsync_url {config["pdb_20200417"]["rsync_url"][:-2]} ' \
                    f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'Failed to RSYNC with the PDB server' in stdout

    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_fail_cleanup(self, tmp_path):
        assert len(os.listdir(tmp_path / 'data')) == 0
        assert len(os.listdir(tmp_path / 'clustering')) == 0

    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupRealPDBMirror:

    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup.py ' \
                    f'-db_path {tmp_path} '

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0 or p.returncode == 1
        if p.returncode == 1:
            assert 'Downloaded file creation timestamp does not match the PDB version' in stdout
        else:
            assert 'Successfully set up localpdb' in stdout

    @pytest.mark.dependency(depends=['TestSetupRealPDBMirror::test_setup_run'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert not os.path.isdir(tmp_path / 'mirror' / 'pdb')

    @pytest.mark.dependency(depends=['TestSetupRealPDBMirror::test_setup_run'])
    def test_setup_cif_rsync(self, tmp_path):
        assert not os.path.isdir(tmp_path / 'mirror' / 'mmCIF')

    @pytest.mark.dependency(depends=['TestSetupRealPDBMirror::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')
