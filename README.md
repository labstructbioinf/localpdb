# localpdb
![localpdb](https://github.com/labstructbioinf/localpdb/workflows/localpdb/badge.svg) 
![localpdb](https://img.shields.io/pypi/v/localpdb)
[![codecov](https://codecov.io/gh/labstructbioinf/localpdb/branch/master/graph/badge.svg)](https://codecov.io/gh/labstructbioinf/localpdb) 
![python-ver](https://img.shields.io/badge/python-%3E=3.6.1-blue)


## Overview
**localpdb** provides a simple framework to store the local mirror of the protein structures available in the [PDB](https://www.rcsb.org/) database and other related resources.

The underlying data can be conveniently browsed and queried with the `pandas.DataFrame` structures. 
Update mechanism allows to follow the weekly PDB releases while retaining the possiblity to access previous data versions.

**You may find `localpdb` particularly useful if you:**

- already use Biopython `Bio.PDB.PDBList`, `prody.proteins.localpdb` modules or tools like 
  [CCPDB](https://webs.iiitd.edu.in/raghava/ccpdb/),
- build custom protein datasets based on multiple criteria, e.g. for machine learning purposes,
- create pipelines based on the multiple or all available protein structures,
- are a fan of pandas `DataFrames`.

![Example1](docs/img/overview.png?raw=true)

## Examples
### Find number of entries added to the PDB every year
```sh
pip install localpdb
localpdb_setup -db_path /path/to/your/localpdb
```
```python
from localpdb import PDB

lpdb = PDB(db_path='/path/to/your/localpdb')
lpdb.entries = lpdb.entries.query('deposition_date.dt.year >= 2015 & deposition_date.dt.year <= 2020')

df = lpdb.entries.groupby(by=['method', lpdb.entries.deposition_date.dt.year])['mmCIF_fn'].count().reset_index()

sns.barplot(data=df, x='deposition_date', y='mmCIF_fn', hue='method')
```
![Example1](docs/img/example1.png?raw=true)

### Create a custom dataset of protein chains
Select **human SAM-dependent methyltransferases**, solved with **X-ray diffraction** with resolution below **2.5 Angstrom** and deposited **after 2010**. Remove the sequence **redundancy at 90%**.
```sh
# Install plugins providing additional data
localpdb_setup -db_path /path/to/your/localpdb -plugins SIFTS ECOD PDBClustering
```
```python
from localpdb import PDB
import gzip

lpdb.entries = lpdb.entries.query('type == "prot"') # Protein structures
lpdb.entries = lpdb.entries.query('method == "diffraction"') # solved with X-ray diffraction
lpdb.entries = lpdb.entries.query('resolution <= 2.5') # with resolution below 2.5A
lpdb.entries = lpdb.entries.query('deposition_date.dt.year >= 2010') # added after 2010
lpdb.chains = lpdb.chains.query('ncbi_taxid == "9606"') # human proteins
lpdb.ecod = lpdb.ecod.query('t_name == "S-adenosyl-L-methionine-dependent methyltransferases"') # SAM dependent methyltransferases

# Remove redundancy (select only representative structure from each sequence cluster)
lpdb.load_clustering_data(redundancy=90)
lpdb.chains = lpdb.chains[lpdb.chains['clust-90'].notnull()]

representative = lpdb.chains.groupby(by='clust-90')['resolution'].idxmin()
lpdb.chains = lpdb.chains.loc[representative]

lpdb.chains.to_csv('dataset.csv') # Save dataset
```
## Advanced examples
### Infer protein dynamics from the ensemble of structures available in PDB
![Example3](docs/img/example3.png?raw=true)