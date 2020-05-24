import yaml
import os
from pathlib import Path


class Config:

    def __init__(self, db_path):
        self.config_fn = Path(db_path) / 'config.yml'
        with open(self.config_fn) as f:
            self.data = yaml.safe_load(f)
        assert 'mirror_pdb' in self.data.keys()
        assert 'mirror_cif' in self.data.keys()

    def commit(self):
        with open(self.config_fn, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False)


def load_remote_source(mirror=''):
    """
    Loads config file with definition of the remote data sources and formats it according to the chosen mirror.
    @return: loaded config dictionary
    """
    my_path = os.path.dirname(os.path.realpath(__file__))
    with open('{}/remote_sources.yml'.format(my_path)) as f:
        config = yaml.safe_load(f)
    mirrors = config.pop('mirrors')
    config.update(mirrors[mirror])
    return config
