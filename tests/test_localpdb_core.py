import yaml
import os
import shlex
import shutil
import subprocess
import pytest
import tempfile
from localpdb import PDB

my_path = os.path.dirname(os.path.realpath(__file__))
with open('{}/test_config.yml'.format(my_path)) as f:
    config = yaml.safe_load(f)


@pytest.fixture(scope='class', autouse=True)
def tmp_path():
    tmp_path = f'{config["tmp_path"]}/{next(tempfile._get_candidate_names())}'
    os.mkdir(tmp_path)
    setup_cmd = f'bin/localpdb_setup.py --fetch_pdb --fetch_cif ' \
                f'-db_path {tmp_path} ' \
                f'-ftp_url {config["pdb_20200417"]["url"]} ' \
                f'-clust_url {config["pdb_20200417"]["clust_url"]} ' \
                f'-rsync_url {config["pdb_20200417"]["rsync_url"]} ' \
                f'-rsync_opts \'{config["pdb_20200417"]["rsync_opts"]}\''
    p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.returncode == 0
    yield tmp_path
    shutil.rmtree(tmp_path)


class TestCorePDB:

    def test_lpdb_loading_basic_behaviour(self, tmp_path):

        # Check simple load from setup data
        lpdb = PDB(db_path=tmp_path)

        # Assert lengths of df's (total data loaded)
        assert len(lpdb.entries) == 159299
        assert len(lpdb.chains) == 515201

        # Assert number of avaialble structures from the mocked RCSB mirror
        assert len(lpdb.entries[lpdb.entries['pdb_fn'].notnull()]) == 246
        assert len(lpdb.entries[lpdb.entries['mmcif_fn'].notnull()]) == 247

        # Assert for simple query
        lpdb.entries = lpdb.entries.query('resolution <= 2.5')
        assert len(lpdb.entries) == 111598
        assert len(lpdb.chains) == 257821

        # Check reset behaviour
        lpdb.reset()
        assert len(lpdb.entries) == 159299
        assert len(lpdb.chains) == 515201

        # Check clustering data handling
        lpdb.load_clustering_data(cutoff=50)
        lpdb.load_clustering_data(cutoff=90)
        assert 'clust-50' in lpdb.chains.columns
        assert 'clust-90' in lpdb.chains.columns
        assert len(lpdb.chains['clust-50'].unique()) == 44303
        with pytest.raises(Exception):
            lpdb.load_clustering_data(cutoff=90)
        with pytest.raises(Exception):
            lpdb.load_clustering_data(cutoff='X')

        assert 'localpdb' in str(lpdb)
        assert '20200417' in str(lpdb)

        lpdb.select_updates()
        assert len(lpdb.entries) == 325

    def test_lpdb_loading_wrong_dir(self, tmp_path):
        with pytest.raises(Exception):
            lpdb = PDB(db_path=tmp_path[0:-1])

    def test_lpdb_loading_wrong_version(self, tmp_path):
        with pytest.raises(Exception):
            lpdb = PDB(db_path=tmp_path, version=1)

    def test_lpdb_loading_wrong_version_2(self, tmp_path):
        with pytest.raises(Exception):
            lpdb = PDB(db_path=tmp_path, version='XXXX')

    def test_lpdb_loading_no_config(self, tmp_path):
        shutil.move(f'{tmp_path}/config.yml', f'{tmp_path}/config.yml.bk')
        with pytest.raises(Exception):
            lpdb = PDB(db_path=tmp_path)
        shutil.move(f'{tmp_path}/config.yml.bk', f'{tmp_path}/config.yml')

    def test_lpdb_loading_malformed_files(self, tmp_path):
        shutil.move(f'{tmp_path}/data/20200417/pdb_entries.txt', f'{tmp_path}/data/20200417/pdb_entries.txt.bk')
        with pytest.raises(Exception):
            lpdb = PDB(db_path=tmp_path)
        shutil.move(f'{tmp_path}/data/20200417/pdb_entries.txt.bk', f'{tmp_path}/data/20200417/pdb_entries.txt')


