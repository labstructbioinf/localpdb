**Amino acid preferences among the viral coiled-coil domains**

```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from localpdb import PDB

lpdb = PDB('/ssd/db/localpdb_dev', plugins=['Socket'])

# Select only viral proteins
lpdb.search(attribute='struct_keywords.pdbx_keywords', operator='contains_phrase', 
            value='VIRAL PROTEIN', no_hits=-1, select=True)
# Select only entries containing coiled-coil domain
lpdb.entries = lpdb.entries[lpdb.entries['socket_7.0'].notnull()]

# Only X-ray entries with resolution higher than 2 A
lpdb.entries = lpdb.entries.query('method == "diffraction"')
lpdb.entries = lpdb.entries.query('resolution <= 2.0')

# Get socket data dictionary
socket = lpdb.get_socket_dict(method='heptads')

stats = {pos: {aa: 0 for aa in 'AILVCDEFGHKMNPQRSTWYX'} for pos in 'abcdefg'}

# Iterate over all coiled-coil domains and compute stats
for entry, ccs in socket.items():
    for cc in ccs.values():
        for seq, hept_register in zip(cc['sequences'].values(), cc['heptads'].values()):
            for aa, hept in zip(seq, hept_register):
                stats[hept][aa] += 1

# Plot
df = pd.DataFrame.from_dict(stats)
plt.figure(figsize=(10, 10))
ax = sns.heatmap(df, cmap='viridis', cbar=False)
ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize = 18)
ax.set_yticklabels(ax.get_ymajorticklabels(), fontsize = 16, rotation=45)
```

![Example2](img/example2.png?raw=true)