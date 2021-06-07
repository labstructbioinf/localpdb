```python
localpdb.PDB.search(attribute, operator, value, return_type='entry', 
                    no_hits=1000, get_doc_only=False, select=False)
```
Performs a basic search using the RCSB API. More information available at the RCSB [website](https://search.rcsb.org/#search-api). ***Returns the DataFrame with entries satisfying the query and, sometimes, additional scoring information.***

Parameter &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description 
:-------------: | ----------------------------------------------------------
**`attribute`** | Attribute to perform a search on - the full list is available [here](https://search.rcsb.org/search-attributes.html).
**`operator`** | Operator to use in the search - full list of operators available with corresponding attributes is available [here](https://search.rcsb.org/search-attributes.html).
**`value`** | Value used in the search.
**`return_type`** | Format of the returned entries that satisfy the query. Available options are `entry` (`PDBID`), `polymer_entity` (`PDBID_ENTITY`), `polymer_instance` (`PDBID_CHAIN`), 
**`no_hits`** | Number of presented hits. Default: `no_hits=1000`, use `no_hits=-1` to get all hits.
**`get_doc_only`** | Present only the dataframe with available attributes and operators.
**`select`** | If True the results of the query will be used to perform selection on `lpdb.entries` (if `return_type=='entries'`) or `lpdb.chains` (if `return_type=='polymer_instance'`). Moreover, if `lpdb` is instantiated with `auto_filter` mode, the selection will be propagated to other registered dataframes.


```python
localpdb.PDB.search_sequence(sequence, evalue=1, identity=0.9, return_type="polymer_instance", 
                             no_hits=1000, select=False)
```
Search for similar sequences to the input sequence among the entries available in the PDB database. ***Returns the DataFrame with sequences similar to the query and similarity statistics.***

Parameter &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description 
:-------------: | ----------------------------------------------------------
**`sequence`** | Input sequence.
**`evalue`** | Minimum e-value to include a sequence.
**`identity`** | Minimum identity to the query to include a sequence.
**`return_type`** | Format of the returned entries that satisfy the query. Available options are `entry` (`PDBID`), `polymer_entity` (`PDBID_ENTITY`), `polymer_instance` (`PDBID_CHAIN`), 
**`no_hits`** | Number of presented hits. Default: `no_hits=1000`, use `no_hits=-1` to get all hits.
**`select`** | If True the results of the query will be used to perform selection on `lpdb.entries` (if `return_type=='entries'`) or `lpdb.chains` (if `return_type=='polymer_instance'`). Moreover, if `lpdb` is instantiated with `auto_filter` mode, the selection will be propagated to other registered dataframes.


```python
localpdb.PDB.search_struct(pdb_id, assembly_id=1, operator='strict_shape_match',
                           return_type="entry",  no_hits=1000, select=False)
```
Search for structures spatially similar to the input structures. ***Returns the DataFrame with structures similar to the query and similarity statistics.***

Parameter &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description 
:-------------: | ----------------------------------------------------------
**`pdb_id`** |  Input structure identifier.
**`assembly_id`** | Assembly identifier of the input structure.
**`operator`** | Match mode type - either `relaxed_shape_match` or `strict_shape_match`.
**`return_type`** | Format of the returned entries that satisfy the query. Available options are `entry` (`PDBID`), `polymer_entity` (`PDBID_ENTITY`), `polymer_instance` (`PDBID_CHAIN`), 
**`no_hits`** | Number of presented hits. Default: `no_hits=1000`, use `no_hits=-1` to get all hits.
**`select`** | If True the results of the query will be used to perform selection on `lpdb.entries` (if `return_type=='entries'`) or `lpdb.chains` (if `return_type=='polymer_instance'`). Moreover, if `lpdb` is instantiated with `auto_filter` mode, the selection will be propagated to other registered dataframes.


```python
localpdb.PDB.search_seq_motif(query, type_='prosite', return_type="entry", no_hits=1000, select=False)
```
Search for a sequence motif in entries available in the PDB database. ***Returns the DataFrame with the entries containing the specified sequence motif.***

Parameter &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Description 
:-------------: | ----------------------------------------------------------
**`query`** | Query motif to find in the PDB sequences, according to given type_ (i.e prosite)
**`type_`** | Type of the specified motif. Available: `simple` (e.g., `CXCXXL`), `prosite` (e.g., `C-X-C-X(2)-[LIVMYFWC]`), `regex` (e.g., `CXCX{2}[LIVMYFWC]`)
**`return_type`** | Format of the returned entries that satisfy the query. Available options are `entry` (`PDBID`), `polymer_entity` (`PDBID_ENTITY`), `polymer_instance` (`PDBID_CHAIN`), 
**`no_hits`** | Number of presented hits. Default: `no_hits=1000`, use `no_hits=-1` to get all hits.
**`select`** | If True the results of the query will be used to perform selection on `lpdb.entries` (if `return_type=='entries'`) or `lpdb.chains` (if `return_type=='polymer_instance'`). Moreover, if `lpdb` is instantiated with `auto_filter` mode, the selection will be propagated to other registered dataframes.
