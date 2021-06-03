# Basic usage
!!! warning
    Please follow the [installation steps](setup.md) before trying to run `localpdb`
 
Once `localpdb` is setup in the preferred directory you can load the underlying data:
```python
from localpdb import PDB
lpdb = PDB(db_path='/path/to/localpdb', version='latest')
```
The `lpdb` object contains two main attributes:

- `lpdb.entries` - protein entries available in the loaded PDB data,
- `lpdb.chains` - individual protein chains available in the loaded PDB data.

!!! Example 
    `lpdb.entries`
    
    |        |**pdb**|**sequence**             |**deposition_date**  |**resolution**|**method**   |
    |:------:|:-----:|:-----------------------:|:-------------------:|:------------:|:-----------:|
    | 2lje_A | 2lje  | GSSHHHHHHSSGLVPRGSHMK...| 2011-09-11 00:00:00 |       nan    | NMR         |
    | 5qc9_A | 5qc9  | ILPDSVDWREKGCVTEVKYQG...| 2017-08-04 00:00:00 |         2    | diffraction |
    | 1yxj_B | 1yxj  | MPCPQDWIWHGENCYLFSSGS...| 2005-02-22 00:00:00 |         1.78 | diffraction |
    | 4d6w_C | 4d6w  | YLSIAFPENTKLDWKPVTKNT...| 2014-11-18 00:00:00 |         3.6  | diffraction |
    | 5wln_K | 5wln  | ENSGGNAFVPAGNQQEAHWTI...| 2017-07-27 00:00:00 |         3.57 | EM          |
    | ... | ...  | ...| ... |         ... | ...          |

