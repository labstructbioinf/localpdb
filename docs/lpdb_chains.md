**`localpdb.PDB.chains`**

| Column &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;            | Description                             |
|:---------------------:|:---------------------------------------:|
| `pdb`                 | PDB identifier, corresponds with `lpdb.entries` DataFrame    |
| `sequence`            | Protein sequence     |
| `deposition_date`     | Date of deposition to PDB               |
| `resolution`          | Resolution (available for methods: `diffraction`, `EM`)        |
| `method`              | Method of structure determination (`diffraction`, `EM`, `NMR`) |
| `fn`                  | Filename of the extracted structure of the chain (requires `PDBChain` plugin) |
| `ncbi_taxid`          | NCBI taxonomy identifier (requires `SIFTS` plugin)  |

!!! Warning
    - The sequence available in the `sequence` column does not necessarily match the sequence in the protein structure. The mapping between these can be obtained with the `PDBSeqresMapper` plugin.
    - In the case of multiple NCBI taxonomy identifiers are mapped to a protein chain, only the first one is presented.


!!! Example
    `lpdb.chains`

    |         | pdb   | sequence                                                                                                                                                                                                                                               | deposition_date     |   resolution | method      |
    |:--------|:------|:-------------------------------------------------|:--------------------|-------------:|:------------|
    | 4ctg_AU | 4ctg  | VTNVGEDGEPGETEPRHALSPVDMHVHTDVSFLLDRFFDVETLE.... | 2014-03-13 00:00:00 |        17    | EM          |
    | 5aol_B  | 5aol  | SSSVPSQKTYQGSYGFRLGFLHSGTAKSVTC...               | 2015-09-10 00:00:00 |         1.5  | diffraction |
    | 1awt_F  | 1awt  | VNPTVFFDIAVDGEPLGRVSFELFADKVPKTAENFRALSTGEKGF... | 1997-10-05 00:00:00 |         2.55 | diffraction |
    | 5bts_A  | 5bts  | GIVEQCCTSICSLYQLENYCN                            | 2015-06-03 00:00:00 |         1.77 | diffraction |
    | 3v4d_E  | 3v4d  | LYFQGHMPKSVIIPAGSSAPLAPFVPGTLADGVVYVSGTLAFD....  | 2011-12-14 00:00:00 |         1.95 | diffraction |

