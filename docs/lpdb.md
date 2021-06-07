**`localpdb.PDB()`**

## Arguments
| Argument &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;    | Description                |
|:-------------|:---------------------------|
|`db_path`      | location of the `localpdb` database |
|`version`      | version of the `localpdb` database to load (default: `version='latest'`) |
| `auto_filter` | automatically propagate selections performed on any of the DataFrames to other DataFrames (default: `auto_filter=True`). See example below for more information. |
|`plugins`      | Names of the plugins to load |

!!! Example
    ```python
    from localpdb import PDB
    lpdb = PDB(db_path='/ssd/db/localpdb', version='latest', auto_filter=True)
    lpdb.entries = lpdb.entries.query(lpdb.entries.query('method == "diffraction"'))
    ```
    `lpdb.entries` was updated and since `auto_filter=True` the selection will be also propagated to `lpdb.chains`.
    In other words `lpdb.chains` will contain only the chains corresponding to the entries present in `lpdb.entries`.

## Attributes

| Attribute     | Description                |
|:-------------|:----------------------------|
| `entries`    |`pandas.DataFrame` containing all entries available in the loaded PDB release. [More info](lpdb_entries.md).
| `chains`     | `pandas.DataFrame` containing all chains (polymer entity instances) in the loaded PDB release. [More info](lpdb_chains.md).
| `version`    | timestamp of the loaded PDB data, in the format `YYYYMMDD` (e.g. `20210507`)


## Methods
| Method  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;   | Description                |
|:-------------|:----------------------------|
| `reset()`    | Resets all selections performed on any of the DataFrames and restores the initial state of PDB object.
| `load_plugin(plugin='Name')` | Loads plugins and its data.
| `select_updates(mode='am+')` | Selects only the entries that were either added (`mode='a'`) or (`mode='m'`) or both (`mode='am'`) in the latest PDB weekly release. In `mode='am+'` updates with respect to the previous localpdb version will be loaded. 
| `search()` | [Info available on separate page](lpdb_search.md)
| `search_seq()` | [Info available on separate page](lpdb_search.md)
| `search_seq_motif()` | [Info available on separate page](lpdb_search.md)
| `search_struct()` | [Info available on separate page](lpdb_search.md)