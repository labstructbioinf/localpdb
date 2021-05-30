import os

import pytest

from localpdb.PDBDownloader import PDBDownloader


class TestPDBDownloader:

    @staticmethod
    def get_downloader(tmp_dir, version, remote_cofig):
        return PDBDownloader(tmp_dir, version, remote_cofig)

    def test_setup_downloader(self, tmp_dir, remote_config):
        downloader = PDBDownloader(tmp_dir, '20210521', remote_config)
        assert downloader.db_path.as_posix() == tmp_dir

    def test_failed_setup_downloader_lock(self, tmp_dir, remote_config):
        os.mknod(os.path.join(tmp_dir, '.lock'))
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            PDBDownloader(tmp_dir, '20210521', remote_config)
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1
