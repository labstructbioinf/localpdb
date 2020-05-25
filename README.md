# localpdb
![localpdb](https://github.com/labstructbioinf/localpdb/workflows/localpdb/badge.svg) 
[![codecov](https://codecov.io/gh/labstructbioinf/localpdb/branch/master/graph/badge.svg)](https://codecov.io/gh/labstructbioinf/localpdb) 
[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

- **Store a local copy of the [PDB](https://www.rcsb.org/) data and [related](#additional-resources) 
protein resources,**
- **Access and query the data convinently through pandas `DataFrame` 
structures,**
- **Update with weekly releases of a new data with full history versioning,**
- **Customize to your needs or add other data sources with simple [plugin](#plugins) system.**

### Quick start
- Install **localpdb** with pip and run setup script to download PDB data and protein structures in the 
PDB format:
```sh
pip3 install localpdb
localpdb_setup.py -db_path /path/to/your/localpdb --fetch_pdb
```
* Simple pipeline that selects for further analysis a representative set of protein structures:
    * solved with X-ray crystallography,
    * with resolution better than 2.5 angstroms, 
    * deposited in 2010 or later, 
    * with redundancy removed at the sequence level.
```python
from localpdb import PDB
import gzip

lpdb = PDB(db_path='/path/to/your/localpdb')

# Select protein structures solved with X-ray diffraction (resolution above 2.5 A)
lpdb.entries = lpdb.entries.query('type == "prot"')
lpdb.entries = lpdb.entries.query('method == "diffraction"')
lpdb.entries = lpdb.entries.query('resolution <= 2.5')
lpdb.entries = lpdb.entries.query('deposition_date.dt.year >= 2010')

# Remove redundancy (select only representative structure from each sequence cluster)
lpdb.load_clustering_data(cutoff=90)
lpdb.chains = lpdb.chains[lpdb.chains['clust-90'].notnull()]

representative = lpdb.chains.groupby(by='clust-90')['resolution'].idxmin()
lpdb.chains = lpdb.chains.loc[representative]

for pdb_fn in lpdb.chains.pdb_fn:
    # your analysis here


```
### Additional resources
**(In development)**
### Plugins
**(In development)**