
## Currently available plugins and description

Current selection of plugins is limited mainly by the scientific interest of our lab. If you would like to include a new data source do not hesitate to contact us or follow a dedicated [guideline](plugin_guide.md).

Plugin &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description 
:-------------: | ----------------------------------------------------------
**`SIFTS`** | Provides an easy access to the [SIFTS](https://www.ebi.ac.uk/pdbe/docs/sifts/overview.html) data. Adds new dataframes `lpdb.pfam`, `lpdb.scop`, `lpdb.ec`, `lpdb.cath` and an additional column in the `lpdb.chains` dataframes containing taxonomy information.
**`Biounit`** | Precalculates the biological assemblies from the raw PDB entries with the [MakeMultimer](http://watcut.uwaterloo.ca/tools/makemultimer/) script.
**`ECOD`** | Provides an access to the [ECOD](http://prodata.swmed.edu/ecod/) data. Adds new dataframe `lpdb.ecod`.
**`DSSP`** | Precalculates the [DSSP](https://swift.cmbi.umcn.nl/gv/dssp/DSSP_3.html) output for each entry in the PDB. Adds a `dssp` in the `lpdb.entries`. 
**`PDBClustering`** | Enables the access to the precomputed clustering results from the [RCSB](https://www.rcsb.org/docs/programmatic-access/file-download-services#sequence-data). Adds the `localpdb.PDB.load_clustering_data` function and subsequently the `clust-*` column(s) in the `lpdb.chains` DataFrame.
**`PDBSeqresMapper`** | Provides the mapping between the names of residues in the PDB/mmCIF file and SEQRES (natural) protein sequence. Mapping is available through the `localpdb.PDB.get_pdbseqres_mapping()` function. 
**`Socket`** | Calculates the coiled-coil domain annotations in the available protein structures with the [Socket](http://coiledcoils.chm.bris.ac.uk/socket/) program. Adds a `localpdb.PDB.get_socket_dict` function that returns the parsed annotation for the current `lpdb.entries` selection.
**`PDBChain`** | Provides an access to the precalculated PDB files corresponding to the individual chains (polymer instances)
