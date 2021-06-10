import yaml
import os
import shlex
import shutil
import subprocess
import pytest
import json
import tempfile
from pathlib import Path
from localpdb import PDB

my_path = os.path.dirname(os.path.realpath(__file__))
with open('{}/test_config.yml'.format(my_path)) as f:
    config = yaml.safe_load(f)


@pytest.fixture(scope='class', autouse=True)
def tmp_path():
    tmp_path = f'/tmp/{next(tempfile._get_candidate_names())}'
    os.mkdir(tmp_path)
    yield Path(tmp_path)
    shutil.rmtree(tmp_path)


class TestUpdateBasic:
    """
    Test basic setup functions using the mocked PDB 'mini-mirror'
    """

    # Setup run
    @pytest.mark.dependency()
    def test_setup(self, tmp_path):
        setup_cmd = f'localpdb_setup -plugins Biounit --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')
        assert p.returncode == 0
        assert 'Successfully set up localpdb' in stdout

    # Test update
    @pytest.mark.dependency(depends=['TestUpdateBasic::test_setup'])
    def test_update(self, tmp_path):
        setup_cmd = f'localpdb_setup --update ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210521"]["url"]} ' \
                    f'-download_proto {config["pdb_20210521"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210521"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210521"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')
        assert p.returncode == 0
        assert 'Successfully updated localpdb' in stdout
        assert 'Successfully installed plugin' in stdout


    # Test number of pdb files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestUpdateBasic::test_setup'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 592
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir) if 'b20210521' in fn]) == 6

    # Test number of mmCIF files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestUpdateBasic::test_setup'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir) ]) == 605
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir) if 'b20210521' in fn]) == 7

    # Check localpdb.PDB basic behavior
    @pytest.mark.dependency(depends=['TestUpdateBasic::test_setup'])
    def test_setup_lpdb_data(self, tmp_path):

        lpdb1 = PDB(tmp_path, version=20210514, plugins=['Biounit'])
        lpdb2 = PDB(tmp_path, version=20210521, plugins=['Biounit'])
        lpdb2.select_updates('m')

        assert all(['b20210521' in fn for fn in lpdb1.entries.loc[lpdb2.entries.index]['mmCIF_fn'].values]) == True

        lpdb2.entries = lpdb2.entries[lpdb2.entries['biounit'].notnull()]
        assert all(['b20210521' in fn for fn in lpdb1.entries.loc[lpdb2.entries.index]['biounit'].values]) == True


class TestUpdateSkipVersions:
    """
    Test basic setup functions using the mocked PDB 'mini-mirror'
    """

    # Test setup run
    @pytest.mark.dependency()
    def test_setup(self, tmp_path):
        setup_cmd = f'localpdb_setup -plugins Biounit --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')
        assert p.returncode == 0
        assert 'Successfully set up localpdb' in stdout

    # Test setup in a directory where localpdb is already setup
    @pytest.mark.dependency(depends=['TestUpdateSkipVersions::test_setup'])
    def test_update(self, tmp_path):
        setup_cmd = f'localpdb_setup --update ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210528"]["url"]} ' \
                    f'-download_proto {config["pdb_20210528"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210528"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210528"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')
        assert p.returncode == 0
        assert 'Successfully updated localpdb' in stdout
        assert 'Successfully installed plugin' in stdout


    # Test number of pdb files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestUpdateSkipVersions::test_setup'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 803
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir) if 'b20210528' in fn]) == 15

    # Test number of mmCIF files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestUpdateSkipVersions::test_setup'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir) ]) == 843
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir) if 'b20210528' in fn]) == 18

    # Check localpdb.PDB basic behavior
    @pytest.mark.dependency(depends=['TestUpdateSkipVersions::test_setup'])
    def test_setup_lpdb_data(self, tmp_path):

        lpdb1 = PDB(tmp_path, version=20210514, plugins=['Biounit'])
        lpdb2 = PDB(tmp_path, version=20210528, plugins=['Biounit'])
        lpdb2.select_updates('m')

        lpdb2.entries = lpdb2.entries[lpdb2.entries['biounit'].notnull()]
        lpdb2.entries = lpdb2.entries[lpdb2.entries['biounit'] != 'not_compatible']
        lpdb1.entries = lpdb1.entries[lpdb1.entries['biounit'].notnull()]
        lpdb1.entries = lpdb1.entries[lpdb1.entries['biounit'] != 'not_compatible']
        lpdb1.entries = lpdb1.entries[lpdb1.entries.index.isin(lpdb2.entries.index)]

        assert all(['b20210528' in fn for fn in lpdb1.entries['mmCIF_fn'].values]) == True
        assert all(['b20210528' in fn for fn in lpdb1.entries['biounit'].values]) == True


