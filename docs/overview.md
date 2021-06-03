# Overview

![Overview](img/overview.png?raw=true)

## Basic setup and functionalities
The simplest `localpdb` setup mode can be obtained by running the following command. 
This will give an access to the `lpdb.entries` and `lpdb.chains` dataframes.

!!! Example
    ```sh
    localpdb_setup -db_path /path/to/localpdb
    ```
In order to sync the protein structures (either in PDB or mmCIF formats), you can rerun `localpdb_setup` **at any time** with following parameters:
!!! Example
    ```sh
    localpdb_setup -db_path /path/to/localpdb --fetch_pdb --fetch_cif
    ```
You can also install plugins providing additional data with `localpdb_setup` (also at any time, not necessarily during the initial setup):

!!! Example
    ```sh
    localpdb_setup -db_path /path/to/localpdb -plugins Plugin1 Plugin2
    ```

## Updates
Every week new entries are added to the PDB database, some are removed or modified. 
To track these changes you can easily update your localpdb database (this'll also update any installed plugins):
!!! Example
    ```sh
    localpdb_setup -db_path /path/to/localpdb --update
    ```
