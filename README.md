# **<span style="font-family: 'Courier New';">localpdb</span>**

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/labstructbioinf/localpdb-mybinder/binder?filepath=readme_example.ipynb)
![localpdb](https://img.shields.io/pypi/v/localpdb)
[![codecov](https://codecov.io/gh/labstructbioinf/localpdb/branch/master/graph/badge.svg)](https://codecov.io/gh/labstructbioinf/localpdb) 
![python-ver](https://img.shields.io/badge/python-%3E=3.6.1-blue)

**localpdb** provides a simple framework to store the local mirror of the protein structures available in the [PDB](https://www.rcsb.org/) database and other related resources.

The underlying data can be conveniently browsed and queried with the `pandas.DataFrame` structures. 
Update mechanism allows to follow the weekly PDB releases while retaining the possiblity to access previous data versions.

**You may find `localpdb` particularly useful if you:**

- already use Biopython `Bio.PDB.PDBList` or similar modules and tools like 
  [CCPDB](https://webs.iiitd.edu.in/raghava/ccpdb/),
- build custom protein datasets based on multiple criteria, e.g. for machine learning purposes,
- create pipelines based on the multiple or all available protein structures,
- are a fan of pandas `DataFrames`.

## Overview
![Overview](docs/img/overview.png?raw=true)
To find more about the package and its functionalities please follow the [docs](https://labstructbioinf.github.io/localpdb/overview).

## Installation

```sh
pip install localpdb
```
Setup the database and sync protein structures in the mmCIF format:
```sh
localpdb_setup -db_path /path/to/localpdb --fetch_cif
```
More information on the setup options are available via [docs](https://labstructbioinf.github.io/localpdb/setup).

## Examples
### Find number of entries added to the PDB every year
```python
from localpdb import PDB

lpdb = PDB(db_path='/path/to/your/localpdb')
lpdb.entries = lpdb.entries.query('deposition_date.dt.year >= 2015 & deposition_date.dt.year <= 2020')

df = lpdb.entries.groupby(by=['method', lpdb.entries.deposition_date.dt.year])['mmCIF_fn'].count().reset_index()

sns.barplot(data=df, x='deposition_date', y='mmCIF_fn', hue='method')
```
![Example1](docs/img/example1.png?raw=true)

### Create a custom dataset of protein chains
Select:

- **human SAM-dependent methyltransferases**, 
- solved with **X-ray diffraction**, 
- with resolution below **2.5 Angstrom**
- deposited **after 2010**. 
- remove the sequence **redundancy at 90%**,
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
lpdb.chains = lpdb.chains.query('50 < sequence.str.len() < 1000') # with defined length range
lpdb.ecod = lpdb.ecod.query('t_name == "S-adenosyl-L-methionine-dependent methyltransferases"') # SAM dependent methyltransferases

# Remove redundancy (select only representative structure from each sequence cluster)
lpdb.load_clustering_data(redundancy=90)
lpdb.chains = lpdb.chains[lpdb.chains['clust-90'].notnull()]

representative = lpdb.chains.groupby(by='clust-90')['resolution'].idxmin()
lpdb.chains = lpdb.chains.loc[representative]

lpdb.chains.to_csv('dataset.csv') # Save dataset
```
### Advanced examples
- [Dynamics of the HIV protease inferred from the PDB structures](https://labstructbioinf.github.io/localpdb/hiv_protease/).
![Example1](docs/img/example3.png?raw=true)
 
- [Amino acid preferences among the viral coiled-coil domains](https://labstructbioinf.github.io/localpdb/viral_ccs/).
![Example2](docs/img/example2.png?raw=true)


## Troubleshooting
In case of any troubles free to [contact us](https://lbs.cent.uw.edu.pl) or [open an issue](https://github.com/labstructbioinf/localpdb/issues).

## Acknowledgments
This work was supported by the National Science Centre grant **2017/27/N/NZ1/00716**.

