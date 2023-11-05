from localpdb import PDB
import argparse
import gzip
import re
import pandas as pd
import warnings
import json
import sys
import gzip
import os
from tqdm import tqdm
warnings.filterwarnings("ignore")
from Bio import pairwise2
from Bio.SubsMat import MatrixInfo as matlist
from concurrent.futures import  ProcessPoolExecutor
from localpdb.plugins import PluginVersioneer

def corr_seq(seq):
    """
    Corrects seqres sequence to map non-std residues to 'X' - this fixes biopython aligner weird behaviour
    :param seq: input sequence
    :return: corrected sequence with non-std residues changed to 'X'
    """
    letters = set(list('ACDEFGHIKLMNPQRSTVWYX'))
    corr_seq = ''.join(['C' if aa.islower() else aa if aa in letters else 'X' for aa in seq])
    return corr_seq


def is_continous(list_):
    """
    Checks whether an arbitrary list is numerically continous, i.e. n, n+1, n+2, ....
    :param pdb_num_list:
    :return:
    """
    try:
        return all([int(list_[i]) == int(list_[i + 1]) - 1 for i in range(0, len(list_) - 1)])
    except ValueError:
        return False


def generate_alignment(seqres_seq, frag_seq):

    frag_seq = corr_seq(frag_seq)
    aln = pairwise2.align.localdd(seqres_seq, frag_seq, matlist.blosum62, -1000, -1000, -11, -1)

    if len(aln) == 0:  # Check if there's and alignment
        return None, None
    else:
        seqres_seq_aln = aln[0][0]
        frag_seq_aln = aln[0][1]
        if seqres_seq != seqres_seq_aln:  # Check if seqres seq is intact
            return None, None
        else:
            return seqres_seq_aln, frag_seq_aln


def generate_mapping(frag_seq_aln, seqres_seq_aln, pdb_nums):
    mapped_seqres_residues_fragment = []  # Indices for mapped seqres residues for the fragment
    mapping_frag = {}  # Temporary dict for storing mapping for a fragment

    c = 0  # Counter for seqres seq positioning
    n = 0  # Counter for PDB fragment seq positioning

    # Generate the mapping
    mismatch = False  # Flag for mismatch in residues
    for aa_seqres_aln, aa_frag_seq_aln in zip(seqres_seq_aln, frag_seq_aln):
        if aa_frag_seq_aln != '-':
            if aa_seqres_aln != aa_frag_seq_aln and aa_frag_seq_aln != 'X' and aa_seqres_aln != 'X':
                mismatch = True
            mapping_frag[pdb_nums[n]] = c
            mapped_seqres_residues_fragment.append(c)
            n += 1
        c += 1
    return mapped_seqres_residues_fragment, mapping_frag, mismatch


def parse_dssp_output(dssp_fn, chain=None):
    """
    Parser for DSSP output files. Returns list of dataframes with continous structural fragments in given PDB chain.
    :param dssp_fn: dssp (v3) output file
    :param chain: chain of the PDB structure to use
    :return: list of dataframes with continous structural fragments in given PDB chain
    """
    with gzip.open(dssp_fn, 'rt') as f:
        lines = [line.rstrip() for line in f.readlines()[28:]]
    try:
        dssp = {int(line[0:5].strip()): {'pdb_num': line[5:11].strip(), 'pdb_chain': line[162:163].strip(),
                                         'pdb_resn': line[13:15].strip()} for line in lines}
    except ValueError:
        return list()
    dssp = pd.DataFrame.from_dict(dssp, orient='index')
    chain_break_idx = dssp.index[dssp['pdb_resn'] == '!*'].tolist()
    chain_break_idx = [0, *chain_break_idx, len(dssp) + 1]
    chains = [dssp.iloc[chain_break_idx[n]:chain_break_idx[n + 1] - 1].copy() for n in
              range(len(chain_break_idx) - 1)]
    chains = [chain for chain in chains if len(chain) > 1]
    chain_map = {}
    for i, chain_ in enumerate(chains):
        assert len(set(filter(lambda val: val != '', chain_.pdb_chain.values))) == 1
        chain_map[chain_.pdb_chain.values[0]] = i

    try:
        dssp = chains[chain_map[chain]].reset_index(drop=True)
        dssp.index = dssp.index + 1
    except KeyError:
        return list()

    try:
        gap_idxs = dssp.index[dssp['pdb_resn'] == '!'].tolist()
        gap_idxs = [0, *gap_idxs, len(dssp) + 1]
        continous_frags = (dssp.iloc[gap_idxs[n]:gap_idxs[n + 1] - 1] for n in range(len(gap_idxs) - 1))
    except IndexError:  # There's only 1 continous fragment
        continous_frags = (dssp)
    return list(continous_frags)


def wrap_mapping(mapping_frag, pdb_nums, mapped_seqres_residues_fragment):

    if is_continous(list(mapping_frag.keys())) and is_continous(list(mapping_frag.values())) and len(
            list(mapping_frag.keys())) > 1:
        mapping_frag = {}
        mapping_frag['{}|{}'.format(pdb_nums[0], pdb_nums[-1])] = '{}|{}'.format(mapped_seqres_residues_fragment[0],
                                                                                 mapped_seqres_residues_fragment[-1])
        return mapping_frag
    else:
        return mapping_frag


def map_pdb_to_seqres(inps):
    """
    Maps pdb sequence to the seqres sequence. Inputs are wrapped to the tuple for multiprocessing.
    :param inps: tuple containing dssp output filename for the pdb chain and respective seqres sequence
    :return: dict containing the mapping and list of start and end indices for continous seqres fragments
    """

    pdbid, seqres_seq, chain, dssp_fn = inps

    fragments = parse_dssp_output(dssp_fn, chain)  # Continous structural fragments in pdb_id
    seqres_seq = corr_seq(seqres_seq)  # Corrected seqres sequence

    # Filter out fragments only containing unknown residues
    fragments_filt = [frag for frag in fragments if set(list(''.join(frag['pdb_resn'].values))) != set(['X'])]

    ordered_tmp_mapping = {} # Order temporary mapping for hole filling with fragments of size < 5
    mapping = {}  # Final mapping

    # List of tuples containining start and end indices for seqres fragments that have continous mapping to PDB
    continous_seqres_fragments = []
    mapped_seqres_residues = []  # Indices of all mapped seqres residues

    for counter, fragment in enumerate(fragments_filt):
        frag_gap = False
        pdb_nums = fragment['pdb_num'].values  # List with pdb numberings in fragment
        frag_seq = ''.join(fragment['pdb_resn'].values)  # Fragment sequence

        # Align fragment sequence and seqres sequence

        seqres_seq_aln, frag_seq_aln = generate_alignment(seqres_seq, frag_seq)

        # Progress only if there's alignment and seqres is full and aligned fragment length is >= 5
        if seqres_seq_aln and frag_seq_aln and len(fragment) >= 5:
            if frag_seq not in frag_seq_aln:
                frag_gap = True
                tmp_mapped_seqres_residues = []
                for match in re.finditer('[A-z]+', frag_seq_aln):
                    tmp_mapped_seqres_residues.append((match.start(), match.end() - 1))

            mapped_seqres_residues_fragment, mapping_frag, mismatch = generate_mapping(frag_seq_aln, seqres_seq_aln,
                                                                                       pdb_nums)

            # Wrap mappings if they are continous to save disk-space
            mapping_frag = wrap_mapping(mapping_frag, pdb_nums, mapped_seqres_residues_fragment)

            # Add to results if there's no mismatch, account for potential gaps in fragment seq
            if not mismatch:
                if frag_gap:
                    for el in tmp_mapped_seqres_residues:
                        continous_seqres_fragments.append(el)
                else:
                    continous_seqres_fragments.append(
                        (mapped_seqres_residues_fragment[0], mapped_seqres_residues_fragment[-1]))
                mapping.update(mapping_frag)
                ordered_tmp_mapping[counter] = (mapped_seqres_residues_fragment[0], mapped_seqres_residues_fragment[-1])

            for el in mapped_seqres_residues_fragment:
                mapped_seqres_residues.append(el)

    for counter, fragment in enumerate(fragments_filt):

        if counter not in ordered_tmp_mapping.keys():
            try:
                gap_start = ordered_tmp_mapping[counter-1][1]
            except KeyError:
                gap_start = 0
            try:
                gap_end = ordered_tmp_mapping[counter+1][0]
            except KeyError:
                gap_end = len(seqres_seq)

            pdb_nums = fragment['pdb_num'].values  # List with pdb numberings in fragment
            frag_seq = ''.join(fragment['pdb_resn'].values)  # Fragment sequence
            chunk_seqres = seqres_seq[gap_start:gap_end]
            no_matches = len(list(re.finditer(frag_seq, chunk_seqres)))
            if no_matches == 1:
                try:
                    index = chunk_seqres.index(frag_seq)
                    index_start, index_stop = gap_start + index, gap_start + index + len(frag_seq)
                    fake_frag_seq_aln = ['-'] * len(seqres_seq)
                    for k, c in enumerate(range(index_start, index_stop)):
                        fake_frag_seq_aln[c] = frag_seq[k]
                    fake_frag_seq_aln = ''.join(fake_frag_seq_aln)
                    mapped_seqres_residues_fragment, mapping_frag, mismatch = generate_mapping(fake_frag_seq_aln,
                                                                                               seqres_seq_aln, pdb_nums)
                    mapping_frag = wrap_mapping(mapping_frag, pdb_nums, mapped_seqres_residues_fragment)
                    continous_seqres_fragments.append(
                        (mapped_seqres_residues_fragment[0], mapped_seqres_residues_fragment[-1]))
                    mapping.update(mapping_frag)
                except TypeError:
                    pass
    # Check if each seqres residue is mapped only once
    if len(set(mapped_seqres_residues)) == len(mapped_seqres_residues):
        return pdbid, mapping, continous_seqres_fragments

    # If not return just ermpty dict
    else:
        return pdbid, {}, ()


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='PDBSeqresMapper setup script')
    parser.add_argument('-db_path', help='localpdb PATH', required=True, metavar='DB_PATH')
    parser.add_argument('-version', help='localpdb VERSION', required=True, type=int, metavar='VERSION')
    parser.add_argument("-max_seq_len", help="Maximum sequence length to process", type=int, default=2000)
    parser.add_argument("-np", help="Number of parallel processes", type=int, default=20)
    args = parser.parse_args()
    
    lpdb = PDB(db_path=args.db_path, version=args.version)
    lpdb.load_plugin('DSSP')
    lpdb.entries = lpdb.entries[lpdb.entries['dssp'].notnull()]

    plugin_dir = f"{args.db_path}/mapping/"
    plv = PluginVersioneer(plugin_dir=plugin_dir)

    if args.version in plv.installed_plugin_versions:
        print(f"Plugin version {args.version} already installed!")
        return None

    print(f"DB version {lpdb.version} contains {len(lpdb.chains)} chains...")
    lpdb.chains = lpdb.chains[lpdb.chains["sequence"].str.len() <= args.max_seq_len]
    print(f"After filtering for sequence length: {len(lpdb.chains)} chains...")

    inps = [(pdb_chain, lpdb.chains.loc[pdb_chain, 'sequence'], pdb_chain[5:], lpdb.entries.loc[pdb_chain[0:4], 'dssp'])
           for pdb_chain in lpdb.chains.index]
    with ProcessPoolExecutor(max_workers=args.np) as executor:
        results = list(tqdm(executor.map(map_pdb_to_seqres, inps), total=len(inps)))

    results = {result[0]: (result[1], result[2]) for result in results}
    failed = [key for key, mapping in results.items() if len(mapping[0]) == 0]
    results_clean = {key: mapping for key, mapping in results.items() if len(mapping[0]) > 0}

    os.makedirs(f"{args.db_path}/mapping/", exist_ok=True)
    out_fn = f'{args.db_path}/mapping/{args.version}.json.gz'

    with gzip.open(out_fn, 'wt') as f:
        f.write(json.dumps(results_clean, indent=4))

    plv.update_logs(args.version)


if __name__ == '__main__':
    main()
