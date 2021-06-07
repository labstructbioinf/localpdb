**`localpdb.PDB.entries`**


| Column &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;            | Description                             |
|:---------------------:|:----------------------------------------|
| `type`                | Type of entry (`prot`, `prot-nuc`)      |
| `method`              | Method of structure determination (`diffraction`, `EM`, `NMR`) |
| `resolution`          | Resolution (available for methods: `diffraction`, `EM`)        |
| `deposition_date`     | Date of deposition to PDB               |
| `pdb_fn`              | Filename of the structure in the PDB format (if structure mirror is available)  |
| `mmCIF_fn`            | Filename of the structure in the mmCIF format (if structure mirror is available)   |
| `biounit`             | Filename of the biological assembly generated with the `MakeMultimer.py` script (requires `Biounit` plugin)   |
| `socket_7.*`          | Filename of the Socket (program detecting coiled-coil domains) output `Biounit` and `Socket` plugins)  |
| `dssp`                | Filename of the DSSP file (requires `DSSP` plugin)   |

!!! Warning
    - Some large protein structures will not be available in the PDB format - in such case there'll be a `np.nan` value in the `pdb_fn` column.
    - Currently entries containing solely the nucleic acids are not shown in the `lpdb.entries`

!!! Example
    `lpdb.entries`

    |      | type     | method      |   resolution | deposition_date     | pdb_fn                                        |
    |:----:|:--------:|:-----------:|:------------:|:-------------------:|:---------------------------------------------:|
    | 4fd7 | prot     | diffraction |        1.8   | 2012-05-26 00:00:00 | /ssd/db/localpdb/mirror/pdb/fd/pdb4fd7.ent.gz |
    | 6gz5 | prot-nuc | EM          |        3.5   | 2018-07-03 00:00:00 | not_compatible                                |
    | 6efv | prot     | diffraction |        2.341 | 2018-08-17 00:00:00 | /ssd/db/localpdb/mirror/pdb/ef/pdb6efv.ent.gz |
    | 3eqb | prot     | diffraction |        2.62  | 2008-09-30 00:00:00 | /ssd/db/localpdb/mirror/pdb/eq/pdb3eqb.ent.gz |
    | 3lq4 | prot     | diffraction |        1.98  | 2010-02-08 00:00:00 | /ssd/db/localpdb/mirror/pdb/lq/pdb3lq4.ent.gz |
    | ...  | ...      | ...         |       ...    | ...                 | ...                                           |
