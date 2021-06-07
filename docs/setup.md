# Installation
### Installing localpdb
The setup of the `localpdb` is simple and straightforward.
Recommended installation way is to use `pip`
(this will also make the `localpdb_setup` script available in your `PATH`):
```sh
pip install localpdb
```
The most recent version of `localpdb` can be installed directly from the repository:
```sh
pip install git+https://github.com/labstructbioinf/localpdb.git
```

### Setting up localpdb
Once installed `localpdb` you need to setup the database in a suitable directory:
```sh
localpdb_setup -db_path /path/to/localpdb
```
Setup script provides additional options if you want to additionally keep the
updatable archive of the raw protein structures in various formats or to select the desired PDB mirror:

Option | Description 
:-------------: | ----------------------------------------------------------
**`-db_path PATH`** | Path to store the `localpdb` database
**`-mirror MIRROR`** | PDB mirror used to download the raw files. Valid options are:<br/> - `rcsb` (RCSB PDB - US - **default**), <br /> - `pdbe` (PDBe - UK), <br /> - `pdbj` (PDBj - Japan)
**`-plugins PLUGINS`** | Install plugins fetching additional data. More on plugins.
**`--fetch_pdb`** | Download the protein structures in the `PDB` format
**`--fetch_cif`** | Download the protein structures in the `mmCIF` format
**`--update`** | Update  `localpdb` database instead of setting up. More on updates.

!!! Example
    **Setting up `localpdb` in directory `/ssd/db/localpdb`, syncing structures in `PDB` and `mmCIF` formats 
    and installing plugins `PDBClustering` and `ECOD`:**
    ```sh
    localpdb_setup -db_path /ssd/db/localpdb --fetch_pdb --fetch_cif -plugins ECOD PDBClustering
    ```

