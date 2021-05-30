import tempfile

import pytest

from localpdb.utils.config import load_remote_source


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def remote_config():
    return load_remote_source('rcsb')
