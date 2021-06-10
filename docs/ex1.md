
**Assessing conformational variability from the ensemble of structures of Sars-COV main protease.**
```python
import gzip
import pytraj as pt
import seaborn as sns
import matplotlib.pyplot as plt

from localpdb import PDB
from Bio.PDB import Select
from Bio.PDB.PDBParser import PDBParser
from Bio.PDB import PDBIO
from sklearn.cluster import KMeans

parser = PDBParser(QUIET=True) # PDB files parser
writer = PDBIO() # PDB files writer

####################################
### HELPER FUNCTIONS AND CLASSES ###
def is_continous(list_):
    """
    Checks whether an arbitrary list is numerically continous, i.e. n, n+1, n+2, ....
    """
    try:
        return all([int(list_[i]) == int(list_[i + 1]) - 1 for i in range(0, len(list_) - 1)])
    except ValueError:
        return False

class CustomSelect(Select):
    """ Only accept the specified chains and residues when saving a PDB structure. """
    def __init__(self, chain, beg_idx, end_idx):
        self.ch, self.beg, self.end = chain, beg_idx, end_idx
        
    def accept_residue(self, residue):
        return (self.beg <= residue.get_id()[1] and self.end >= residue.get_id()[1])

    def accept_atom(self, atom):
        if (not atom.is_disordered()) or atom.get_altloc() == 'A' or atom.get_altloc() == '1':
            atom.set_altloc(' ')
            if atom.get_name() == 'CA':
                return True
        return False
    
    def accept_chain(self, chain):
        return chain.get_id() == self.ch
################################
################################

lpdb = PDB('/ssd/db/localpdb_dev', plugins=['PDBSeqresMapper']) # Load localpdb and the Mapper plugin
seq = 'SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRVIGHSMQNCVLKLKVDTANPKTPKYKFVRIQPGQTFSVLACYNGSPSGVYQCAMRPNFTIKGSFLNGSCGSVGFNIDYDCVSFCYMHHMELPTGVHAGTDLEGNFYGPFVDRQTAQAAGTDTTITVNVLAWLYAAVINGDRWFLNRFTTTLNDFNLVAMKYNYEPLTQDHVDILGPLSAQTGIAVLDMCASLKELLQNGMNGRTILGSALLEDEFTPFDVVRQCSGVTFQ'

# Search entries that match the input sequence with 100% identity
lpdb.search_seq(sequence=seq, identity=1, select=True) 

# Iterate over all entries and save coordinates only with the CA atoms
# Extract only the CA atoms that correspond to the 5-295 residue range according to the natural sequence.
fns = []
for pdb_chain, sequence in lpdb.chains['sequence'].to_dict().items():
    pdb, chain = pdb_chain.split('_')
    mapping = lpdb.get_pdbseqres_mapping(pdb_chain, reverse=True)
    indices = (mapping[5], mapping[295]) if is_continous(list(mapping.keys())) else None
    if indices:
        beg, end = indices
        with gzip.open(lpdb.entries.loc[pdb, 'pdb_fn'], 'rt') as f:
            s = parser.get_structure('s', f)[0]
        writer.set_structure(s)
        writer.save(f'CA/{pdb_chain}.pdb', select=CustomSelect(chain, int(beg), int(end)))
        fns.append(f'CA/{pdb_chain}.pdb')

# Use pytraj to perform PCA
traj = pt.load(fns, top=fns[0])
pca = pt.pca(traj, '@CA', n_vecs=2, fit=True, ref=0)

# Cluster the PCA representation
km = KMeans(n_clusters=4)
km.fit(pca[0].T) 

# Plot
sns.kdeplot(pca[0][0], pca[0][1], thresh=.1, linewidth =  0.1)
plt.scatter(pca[0][0], pca[0][1], s=25, c=km.labels_)
plt.xlabel(r'PC1 ($\AA$)', fontsize=14)
plt.ylabel(r'PC2 ($\AA$)', fontsize=14)
plt.savefig('PCA.png', dpi=300)
```

![Example1](img/example3.png?raw=true)