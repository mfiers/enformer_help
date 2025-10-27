# Few helper routines to ease running
# enformer

__version__ = "0.1.0"

import hashlib
import os
from pathlib import Path
import pickle
import gzip

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# For reading local genome files
import pysam

# Run enformer
from enformer_pytorch import Enformer, from_pretrained, str_to_one_hot, seq_indices_to_one_hot
from enformer_pytorch.data import str_to_seq_indices


cache_folder = Path(__file__).parent.parent / 'cache'
dna_cache = cache_folder / 'dna'
enf_cache = cache_folder / 'enformer'

if not dna_cache.exists():
    dna_cache.mkdir()

if not enf_cache.exists():
    enf_cache.mkdir()

# Local genome file paths
GENOME_PATHS = {
    'hg19': '/data/db/genomes/hg19/fasta/hg19.fa',
    'hg38': '/data/db/genomes/hg38/fasta/hg38.fa',  # Add other genomes as needed
}

# Cache for pysam FastaFile objects to avoid reopening
_FASTA_CACHE = {}


mouse_tracks = pd.read_pickle(cache_folder / './targets_mouse.pkl')
human_tracks = pd.read_pickle(cache_folder / './targets_human.pkl')


def search_tracks(keyword, data=False):
    """
    Helper function to search through available tracks.
    """

    m = mouse_tracks[mouse_tracks['description'].str.lower().str.contains(keyword.lower())]
    h = human_tracks[human_tracks['description'].str.lower().str.contains(keyword.lower())]
    cols = "index description".split()

    if data:
        rv = {}
        rv['mouse'] = m
        rv['human'] = h
        return rv
    
    if len(m[cols]) > 0:
        print(f"## Mouse (total tracks: {mouse_tracks.shape[0]})")
        print(m[cols].head())
    if len(h[cols]) > 0:
        print(f"## Human (total tracks: {human_tracks.shape[0]})")
        print(h[cols].head())


    
def getseq(region='chr19:44,900,254-44,911,047', genome='hg19', length=196_608,
           silent=False):
    """
    Retrieve sequence from local genome file

    Given that Enformer requires a window of exactly 196,608 nucleotides
    this code grows (or shrinks) the requested window to exactly that
    size around the center of the requested area.
    """
    chrom, coords = region.strip().split(':')
    start, stop = coords.split('-')
    start = int(start.replace(',', ''))
    stop = int(stop.replace(',', ''))

    if not silent:
        print(f"Requested coordinates {chrom} from {start:_d} to "
              f"{stop:_d} of length: {stop - start + 1:_d}")


    # grow (or shrink) so we get a block of 196,608 exactly
    center = ( (stop - start) // 2 ) + start
    new_start = center - (196_608 // 2)
    new_stop = center + (196_608 // 2)

    if not silent and (new_start != start or new_stop != stop):


        print(f"Fixing window to {chrom} from {new_start:_d} to {new_stop:_d} ", end='')
        print(f"to ensure block length of {new_stop - new_start:_d}")

    # check if the sequence is already in the cache - if so return that
    cache_file = dna_cache / f"{genome}__{chrom}_{new_start}_{new_stop}.pkl.gz"
    if cache_file.exists():
        with gzip.open(cache_file, 'rb') as F:
            return pickle.load(F)

    # Get sequence from local genome file using pysam
    if genome not in GENOME_PATHS:
        raise ValueError(f"Genome '{genome}' not configured. Available: {list(GENOME_PATHS.keys())}")

    genome_path = GENOME_PATHS[genome]
    if not os.path.exists(genome_path):
        raise FileNotFoundError(f"Genome file not found: {genome_path}")

    # Use cached FastaFile object if available
    if genome not in _FASTA_CACHE:
        _FASTA_CACHE[genome] = pysam.FastaFile(genome_path)

    fasta = _FASTA_CACHE[genome]

    # Both pysam and the cache use 0-based half-open coordinates [start, end)
    # new_start and new_stop are already in this format
    dna = fasta.fetch(chrom, new_start, new_stop).upper()

    # save to cache - but only if we have write permissions:
    if os.access(dna_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(dna, F)

    return dna


PREP = False

if PREP:
    ENFORMER = from_pretrained('/data/teachers/software/enformer_help/cache/hub/enformer', use_tf_gamma=True)
else:
    ENFORMER = None

    
def run_enformer_prep(sequence):

    # get hash
    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    # cache_file
    cache_file = enf_cache / f"{sha}.pkl.gz"    

    if cache_file.exists():
        with gzip.open(cache_file, 'rb') as F:
            return pickle.load(F)

    tensor_seq = seq_indices_to_one_hot(str_to_seq_indices(sequence).unsqueeze(0))

    output_seq = ENFORMER(tensor_seq)

    del tensor_seq

    # save to cache - but only if we have write permissions:
    if os.access(enf_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(output_seq, F)


ENFO=None

def run_enformer_keep_in_memory(sequence, silent=True):

    # get hash
    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    # cache_file
    cache_file = enf_cache / f"{sha}.pkl.gz"    

    if cache_file.exists():
        if not silent:
            print('Returning pre-cached enformer object')
        with gzip.open(cache_file, 'rb') as F:
            return pickle.load(F)
        
    global ENFO
    if ENFO is None:
        if not silent:
            print('Loading enformer into memory')
        ENFO = from_pretrained('/data/teachers/software/enformer_help/cache/hub/enformer', use_tf_gamma=True)

    if not silent:
        print("Preparing tensor")
    tensor_seq = seq_indices_to_one_hot(str_to_seq_indices(sequence).unsqueeze(0))

    if not silent:
        print('Execute enformer')
    output_seq = ENFO(tensor_seq)

    del tensor_seq
    if not silent:
        print("Ready!")

    # save to cache - but only if we have write permissions:
    if os.access(enf_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(output_seq, F)

    return output_seq

def run_enformer(sequence, silent=False):

    # get hash
    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    # cache_file
    cache_file = enf_cache / f"{sha}.pkl.gz"    

    if cache_file.exists():
        if not silent:
            print('Returning pre-cached enformer object')
        with gzip.open(cache_file, 'rb') as F:
            return pickle.load(F)
        
    if not silent:
        print('Loading enformer into memory')
    enformer = from_pretrained('/data/teachers/software/enformer_help/cache/hub/enformer', use_tf_gamma=True)

    if not silent:
        print("Preparing tensor")
    tensor_seq = seq_indices_to_one_hot(str_to_seq_indices(sequence).unsqueeze(0))

    if not silent:
        print('Execute enformer')
    output_seq = enformer(tensor_seq)

    if not silent:
        print("Clean up memory")
    del enformer, tensor_seq
    if not silent:
        print("Ready!")

    # save to cache - but only if we have write permissions:
    if os.access(enf_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(output_seq, F)

    return output_seq


# easiest way to check if something happenend is by plotting
# so here is a plot helper function:
def trackplot(title, track, snp_pos=None,
              marks = None):

    dat = pd.DataFrame(dict(y=track.detach().numpy()))
    dat['i'] = range(len(dat))
    dat['x'] = dat['i'] * 128 + snp_pos - 57344
    fig = plt.figure(figsize=(12,2))
    ax = plt.gca()
    dat.plot.scatter(x='x', y='y', s=8, c='k', ax=ax)
    midy = (dat['y'].max() - dat['y'].min()) / 2 + dat['y'].min()
    if snp_pos is not None:
        ax.axvline(snp_pos, zorder=-1, c='grey')
        ax.text(snp_pos, midy, ' snp', va='top')

    if marks is not None:
        for pos, col, name in marks:
            ax.axvline(pos, zorder=-1, c=col, alpha=0.5)
            ax.text(pos, midy, f' {name} ', ha='right', va='top')
            #19440238

    plt.title(title)
