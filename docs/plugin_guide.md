## Overview
Here we'll demonstrate how to create a custom plugin that allows to add to `localpdb` an additional data source.
As an example we'll use the already available plugin integrating results of the clustering of PDB sequences made available by RCSB
([Link](https://www.rcsb.org/docs/programmatic-access/file-download-services#sequence-clusters-data)).

This overview captures only the main aspects. If you run into any troubles while implementing a plugin for a specific data
source feel free to open up an [issue](https://github.com/labstructbioinf/localpdb/issue) or get in touch with developers.

## Definition of the plugin

Plugins should be located in the directory `localpdb/plugins/`. Additional config of the plugin should be stored in the
`localpdb/plugins/config` directory. Name of the plugin python file and config YAML file must match.

## Header of the plugin file
Following the above instruction we create two files - `localpdb/plugins/PDBClustering.py` and `localpdb/plugins/config/PDBClustering.yml`.

Header of the `PDBClustering.py` specifies necessary imports and those specific to the plugin:

```python
import logging
import os
from .Plugin import Plugin
from localpdb.utils.config import Config
from localpdb.utils.os import create_directory

logger = logging.getLogger(__name__)

# Plugin specific imports
from localpdb.utils.network import download_url
```

## Main contents of the plugin file
Subsequently, we define a plugin class that we'll discuss in detail below.
```python
class PDBClustering(Plugin):

    ### Beginning of the part required for proper plugin handling ###
    #################################################################
    plugin_name = os.path.basename(__file__).split('.')[0] # Name of the plugin based on the filename
    plugin_config = Config(
        f'{os.path.dirname(os.path.realpath(__file__))}/config/{plugin_name}.yml').data  # Plugin config (dict)
    plugin_dir = plugin_config['path']
    ###########################################################
    ### End of the part required for proper plugin handling ###

    def __init__(self, lpdb):
        super().__init__(lpdb)

    def _load(self):
        self.lpdb.load_clustering_data = self.load_clustering_data.__get__(self)

    def _prep_paths(self):
        create_directory(f'{self.plugin_dir}/')
        create_directory(f'{self.plugin_dir}/{self.plugin_version}')

    def _setup(self):
        clust_redundancy = [30, 40, 50, 70, 90, 95, 100]
        for redundancy in clust_redundancy:
            local_fn = f'{self.plugin_dir}/{self.plugin_version}/bc-{redundancy}.out'
            url = self.plugin_config['clust_url'] + f'bc-{redundancy}.out'
            download_url(url, local_fn)

    def _reset(self):
        self._load()

    def load_clustering_data(self, redundancy=50):
        valid_cutoffs = ['30', '40', '50', '70', '90', '95', '100']
        if not str(redundancy) in valid_cutoffs:
            cutoffs = ', '.join(valid_cutoffs)
            raise ValueError(f'Cutoff \'{redundancy}\' is not a valid PDB clustering cutoff! Use any of the following: {cutoffs}')
        fn = f'{self.plugin_dir}/{self.plugin_version}/bc-{redundancy}.out'
        _, pdb_idxs = self.lpdb._get_current_indexes()
        cluster_data_filt = {key: value for key, value in parse_cluster_data(fn).items() if key in pdb_idxs}
        self.lpdb._add_col_chains(cluster_data_filt, [f'clust-{redundancy}'])
```
Each plugin must at least implement `_setup()` and `_load()` methods.

### The `_setup()` method

Setup function handles download / processing of the data related to plugin. Directory storing the plugin related files is defined in the 
`path` key of the config file (available via the `plugin_dir` attribute). Importantly, it is up to the user to
account for the proper versioning. Withing the `Plugin` class there's an attribute `plugin_version` specifying for which 
`localpdb` version the plugin is currently set up (or loaded). Any exceptions raised during the setup will be caught by the installer and, in case the run fails,
the setup will not finish.

In the config file one can specify two important boolean keys - `available_historical_versions` and `allow_loading_outdated`.

In many cases, the plugin data is available only for the current PDB version (i.e. it is not possible download this data retrospectively).
Specifying this flag as `available_historical_versions` as `False` will force the plugin installer to try to download the data
only for the current PDB version and skip the rest (if available). 

On the other hand, `allow_loading_outdated` specifies whether it is
allowed to load the older plugin data when exact version is not available (e.g. to load `PDBClustering` data from `20210730` release to
`localpdb` version `20210814`). Since the clustering data is sensitive to even small changes it is disabled in this case, however it may be
reasonable to enable it for plugins that are released not in a weekly cycle (e.g. `ECOD`).

### The `_load()` method
The `_load()` method is responsible for correct plugin loading to `localpdb.PDB` instance. 

In case of the `PDBClustering` the plugin donates a new method - `load_clustering_data()` (implemented within the plugin) 
that allows to load correct version of the data on demand within the `localpdb.PDB` object. In turn, the `load_clustering_data()`
method utilizes the `localpdb.PDB._add_col_chains` method to create a new column within the `localpdb.PDB.chains` DataFrame. 

This mechanism allows to load the data on demand, specifying the necessary parameters (in this case the clustering similarity threshold). In other
cases it may be more reasonable to load the data as additional DataFrame and registering a devoted attribute (e.g. `localpdb.PDB.ecod`.
Again `localpdb` leaves a lot of space here, depending on the actual use case and nature of the data.

### Other methods

Any plugin can implement a `_prep_paths()` method that is responsible for creating a directory tree related to the plugin data. 
This method is called during each plugin setup / update and may be particularly useful if data consists of multiple files or
splitting between different directories is needed.

A `_reset()` method is responsible for the plugin behavior during the `localpdb.PDB.reset()` call. By default a whole plugin
is reloaded in such cases, however it may be more reasonable (in case of e.g. large data files and long load times) to cache
some of the data to persist through the reset without reloading.

Finally, there are `_filter_chains()` and `_filter_entries()` methods. In case when plugin registers a certain attribute
(e.g. ECOD plugin) there's an option that allows to propagate selections done on main DataFrames (`localpdb.PDB.entries` and
`localpdb.PDB.chains`) to any registered attribute. The aforementioned methods allow to implement logic that allows to keep
plugin data and current state of the `localpdb.PDB` object uniform.
