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


class TestSetupBasic:
    """
    Test basic setup functions using the mocked PDB 'mini-mirror'
    """

    # Test setup run
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
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
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_in_already_setup_dir(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'localpdb is up to date and set up in the directory' in stdout

    # Test setup in a directory where localpdb is already setup but the version is most recent (update suggestion).
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_in_already_setup_outdated(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210521"]["url"]} ' \
                    f'-download_proto {config["pdb_20210521"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210521"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210521"]["rsync_opts"]}\''
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'but is not up to date. Consider an update!' in stdout

    # Test number of pdb files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_pdb_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'pdb') for fn in
                    os.listdir(tmp_path / 'mirror' / 'pdb' / sub_dir)]) == 294

    # Test number of mmCIF files rsynced from the mirror
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_cif_rsync(self, tmp_path):
        assert len([fn for sub_dir in os.listdir(tmp_path / 'mirror' / 'mmCIF') for fn in
                    os.listdir(tmp_path / 'mirror' / 'mmCIF' / sub_dir)]) == 300

    # Test whether ".lock" file was successfully removed
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    # Check localpdb.PDB basic behavior
    @pytest.mark.dependency(depends=['TestSetupBasic::test_setup_run'])
    def test_setup_lpdb_data(self, tmp_path):

        lpdb = PDB(tmp_path, auto_filter=True)

        assert lpdb.version == 20210514 # Check version
        assert len(lpdb.entries) == 173845 # Check number of entries
        assert len(lpdb.chains) == 591481 # Check number of chains
        assert len(lpdb.entries[lpdb.entries['mmCIF_fn'].notnull()]) == 300 # Check number of synced mmCIF files

        lpdb.entries = lpdb.entries.loc[['2ftq', '1i00']] # Perform simple selection...
        assert len(lpdb.entries) == 2 # ... and check number of entries
        assert len(lpdb.chains) == 3 # and chains (lpdb.chains should be adjusted accordingly).

        lpdb.reset() # Test reset, number of entries and chains should be as in the begining
        assert len(lpdb.entries) == 173845
        assert len(lpdb.chains) == 591481

        lpdb.select_updates(mode='m') # Test update selection (modified entries)
        assert len(lpdb.entries) == 5
        assert len(lpdb.chains) == 88
        lpdb.reset()

        lpdb.select_updates(mode='a') # Test update selection (added entries)
        assert len(lpdb.entries) == 255
        assert len(lpdb.chains) == 1185


class TestSetupWrongBaseUrl:
    """
    Test setup behaviour when using wrong FTP/HTTP data url address
    """

    # Run setup, should fail in this case
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"][1:]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'Could not connect to the FTP server.' in stdout

    # Check if ".lock" file was correctly removed
    @pytest.mark.dependency(depends=['TestSetupWrongBaseUrl::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    # Check that config file was not generated
    @pytest.mark.dependency(depends=['TestSetupWrongBaseUrl::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupWrongBaseDir:
    """
    Test setup behaviour when using wrong FTP/HTTP directory
    """
    # Run setup, should fail in this case
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"][:-2]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'No valid PDB data found in the remote source.' in stdout

    # Check if ".lock" file was correctly removed
    @pytest.mark.dependency(depends=['TestSetupWrongBaseDir::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    # Check that config file was not generated
    @pytest.mark.dependency(depends=['TestSetupWrongBaseDir::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupWrongRsyncUrl:
    """
    Test setup behaviour when using wrong RSYNC url. In this case the setup should succeed in downloading FTP/HTTP files
    however failing at the mirror RSYNC-ing.
    """
    # Run setup with wrong rsync URL
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"][:-2]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 1
        assert 'Successfully set up localpdb' in stdout
        assert 'Failed to RSYNC with the PDB server' in stdout

    # Verify ".lock" file was correctly removed
    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    # Verify that number of files is correct
    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_fail_cleanup(self, tmp_path):
        assert len(os.listdir(tmp_path / 'data')) == 3

    # Verify that the config file was generated correctly
    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        with open('{}/config.yml'.format(tmp_path)) as f:
            conf = yaml.safe_load(f)
        assert conf['init_ver'] == 20210514
        assert conf['struct_mirror']['pdb'] is False
        assert conf['struct_mirror']['cif'] is False
        assert conf['struct_mirror']['pdb_init_ver'] is None
        assert conf['struct_mirror']['cif_init_ver'] is None

    # Now try again with correct RSYNC url. Files should be synced correctly.
    @pytest.mark.dependency(depends=['TestSetupWrongRsyncUrl::test_setup_run'])
    def test_setup_run_repeated(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode == 0
        assert 'Successfully synced protein structures' in stdout

        # Verify config again
        with open('{}/config.yml'.format(tmp_path)) as f:
            conf = yaml.safe_load(f)
        assert conf['init_ver'] == 20210514
        assert conf['struct_mirror']['pdb'] is True
        assert conf['struct_mirror']['cif'] is True
        assert conf['struct_mirror']['pdb_init_ver'] == 20210514
        assert conf['struct_mirror']['cif_init_ver'] == 20210514


class TestSetupInterrupt:
    """
    Test setup behaviour when using wrong FTP/HTTP directory
    """
    # Run setup and interrupt it after 10s
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'timeout 10s localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\''

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert p.returncode > 0
        assert 'Script abruptly terminated! Cleaning temporary' in stdout

    # Check if ".lock" file was correctly removed
    @pytest.mark.dependency(depends=['TestSetupInterrupt::test_setup_run'])
    def test_setup_lock_absent(self, tmp_path):
        assert not os.path.isfile(tmp_path / '.lock')

    # Check that config file was not generated
    @pytest.mark.dependency(depends=['TestSetupInterrupt::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        assert not os.path.isfile(tmp_path / 'config.yml')


class TestSetupPlugins:
    """
    Test setup behaviour with plugins
    """
    # Run setup without syncing files
    @pytest.mark.dependency()
    def test_setup_run(self, tmp_path):
        setup_cmd = f'localpdb_setup ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\' '
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert p.returncode == 0

    # Try installing plugin that requires syncing PDB files
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_run_plugin1(self, tmp_path):
        setup_cmd = f'localpdb_setup ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\' ' \
                    f'-plugins Biounit'

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert 'requires a local copy of structure files in the PDB format' in stdout

    # Try installing plugin that doesn't require local mirror
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_run_plugin2(self, tmp_path):
        setup_cmd = f'localpdb_setup ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\' ' \
                    f'-plugins ECOD'

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert 'Successfully installed plugin' in stdout

    # Sync structures
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_run2(self, tmp_path):
        setup_cmd = f'localpdb_setup --fetch_pdb --fetch_cif ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\' '
        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert p.returncode == 0

    # Try installing plugin that requires syncing PDB files again
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_run_plugin3(self, tmp_path):
        setup_cmd = f'localpdb_setup ' \
                    f'-db_path {tmp_path} ' \
                    f'-ftp_url {config["pdb_20210514"]["url"]} ' \
                    f'-download_proto {config["pdb_20210514"]["download_proto"]} ' \
                    f'-rsync_url {config["pdb_20210514"]["rsync_url"]} ' \
                    f'-rsync_opts \'{config["pdb_20210514"]["rsync_opts"]}\' ' \
                    f'-plugins Biounit'

        p = subprocess.run(shlex.split(setup_cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = p.stdout.decode('utf-8')

        assert 'Successfully installed plugin' in stdout



    # Check lpdb behavior with plugins
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_lpdb_data(self, tmp_path):
        lpdb = PDB(tmp_path, auto_filter=True, plugins=['ECOD', 'Biounit'])

        # Check number of calculated biounit files
        assert len(
            lpdb.entries[(lpdb.entries['biounit'].notnull()) & (lpdb.entries['biounit'] != 'not_compatible')]) == 292
        # Check autofiltering with ECOD
        lpdb.ecod = lpdb.ecod[lpdb.ecod['x_name'] == 'cradle loop barrel']
        assert len(lpdb.ecod) == 21270
        assert len(lpdb.chains) == 18607
        assert len(lpdb.entries) == 9428

        # Check again after reset
        lpdb.reset()
        assert len(lpdb.entries) == 173845
        assert len(lpdb.chains) == 591481
        assert len(lpdb.ecod) == 791299

    # Check that config file was not generated
    @pytest.mark.dependency(depends=['TestSetupPlugins::test_setup_run'])
    def test_setup_config_gen(self, tmp_path):
        with open('{}/config.yml'.format(tmp_path)) as f:
            conf = yaml.safe_load(f)
        assert 'ECOD' in  conf['plugins']
        assert 'Biounit' in conf['plugins']