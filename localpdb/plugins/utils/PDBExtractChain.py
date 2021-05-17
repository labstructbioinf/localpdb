from Bio.PDB import Select
from Bio.PDB.PDBParser import PDBParser
from Bio.PDB import PDBIO
import os
import argparse
import gzip
import sys


class SelectChains(Select):
    """ Only accept the specified chains when saving. """

    def __init__(self, chain_letters):
        self.chain_letters = chain_letters

    def accept_atom(self, atom):
        if (not atom.is_disordered()) or atom.get_altloc() == 'A' or atom.get_altloc() == '1':
            atom.set_altloc(' ')  # Eliminate alt location ID before output.
            return True
        else:  # Alt location was not one to be output.
            return False

    def accept_chain(self, chain):
        return (chain.get_id() in self.chain_letters)


parser = argparse.ArgumentParser(description='pdb-extract-chain')
parser.add_argument('-i',
                    help='Input file',
                    required=True,
                    metavar='INPUT')
parser.add_argument('-chain',
                    help='Chain to extract',
                    required=True,
                    metavar='CHAIN')
parser.add_argument('-o',
                    help='Output file',
                    required=True,
                    metavar='OUTPUT')
args = parser.parse_args()

parser = PDBParser(QUIET=True)
writer = PDBIO()
with gzip.open(args.i, 'rt') as f:
    struct = parser.get_structure('A', f)
writer.set_structure(struct)
writer.save(args.o, select=SelectChains(args.chain))
os.system('gzip {}'.format(args.o))
try:
    gzip.open('{}.gz'.format(args.o), 'rt').read()
except OSError:
    os.system('rm {}.gz'.format(args.o))
    sys.exit(1)