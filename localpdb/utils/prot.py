import re
import gzip
import os
import pandas as pd
import numpy as np

nuc_re = re.compile(r'[^ATGCUXNIF.]')
nonstd_re = re.compile(r'[^X.]')


def parse_pdb_data(entries_fn, entries_type_fn, res_fn, seqres_fn):
    """
    Builds dataframe with the parsed raw PDB data
    @param entries_fn: filename of the entries.idx file
    @param entries_type_fn:  filename of the pdb_entry_type.txt file
    @param res_fn: filename of the resolution.idx file
    @param seqres_fn: filename of the pdb_seqres fasta file
    @return: basic dataframes with per-structure and per-chain information
    """
    switch = os.path.isfile(entries_type_fn) # Switch for maintaining backwards compatibility with 0.1 versions
    if not switch:
        entries_type_fn = entries_fn
    with open(entries_type_fn) as f:
        entries_type = {key: (type_, method) for (key, type_, method) in list(map(str.split, f.readlines()))}
    entries_type = pd.DataFrame.from_dict(entries_type, orient='index', columns=['type', 'method'])

    with open(res_fn) as f:
        resolution = {data[0].lower(): float(data[2]) for data in list(map(str.split, f.readlines()[6:])) if
                      len(data) == 3}
    resolution = pd.DataFrame.from_dict(resolution, orient='index', columns=['resolution'])

    # Join data into one dataframe
    df_struct = pd.merge(entries_type, resolution, left_index=True, right_index=True)
    if switch: # Backwards compatibility
        with open(entries_fn) as f:
            entries_data = {entry[0].lower(): entry[2] for entry in [line.split('\t') for line in f.readlines()[3:]]}
        entries_data = pd.DataFrame.from_dict(entries_data, orient='index', columns=['deposition_date'])
        entries_data['deposition_date'] = pd.to_datetime(entries_data['deposition_date'])
        df_struct = pd.merge(df_struct, entries_data, left_index=True, right_index=True)

    df_struct = df_struct[df_struct['type'].isin(['prot', 'prot-nuc'])]
    df_struct = df_struct[df_struct['method'].isin(['diffraction', 'NMR', 'EM'])]
    df_struct['resolution'] = df_struct['resolution'].map(lambda x: x if x > 0 else np.nan)

    # Create dataframe with data in a 'per-chain' format
    pdb_ids = set(df_struct.index.values)
    id_seq = {entry[0]: (entry[0][0:4], entry[1]) for entry in parse_gz_fasta(seqres_fn) if
              entry[0][0:4] in pdb_ids}
    df_chain = pd.DataFrame.from_dict(id_seq, orient='index', columns=['pdb', 'sequence'])
    if switch:
        df_chain = pd.merge(df_chain, df_struct[['deposition_date', 'resolution', 'method']], left_on='pdb',
                            right_index=True)
    else:
        df_chain = pd.merge(df_chain, df_struct[['resolution', 'method']], left_on='pdb',
                            right_index=True)

    # Filter chains with nucleic acids or containing only non-standard residues
    df_chain = df_chain[~df_chain['sequence'].map(lambda x: is_nucl_seq(x))]
    df_chain = df_chain[~df_chain['sequence'].map(lambda x: is_nonstd_seq(x))]
    df_struct = df_struct.loc[list(set(df_chain['pdb'].values.tolist()))]

    # Return results
    return df_struct, df_chain


def is_nucl_seq(seq):
    """
    Determines whether sequence is nucleic acid sequence
    :param seq: sequence to check
    :return: True/False
    """

    res = nuc_re.search(seq)
    return not bool(res)


def is_nonstd_seq(seq):
    """
    Determines whether sequence contains unknown ('X') residues
    :param seq: sequence to check
    :return: True/False
    """
    res = nonstd_re.search(seq)
    return not bool(res)


def parse_gz_fasta(fn):
    """
    Parser for PDB seqres fasta files. Faster than the Bio.SeqIO due to cleaned input format.
    @param fn: filename with seqres records from the PDB
    @return: (pdb_chain, sequence) pairs
    """
    with gzip.open(fn, 'rt') as f:
        data = f.readlines()
        for i in range(0, len(data), 2):
            pdb_chain = data[i].split()[0][1:]
            seq = data[i+1].rstrip()
            yield pdb_chain, seq
