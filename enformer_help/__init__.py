# Few helper routines to ease running
# enformer

import hashlib
import os
from pathlib import Path
import pickle
import gzip

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# To interact with UCSC, get sequence data
from ucsc.api import Hub, Genome, Track, TrackSchema, Chromosome, Sequence  

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


mouse_tracks = pd.read_pickle(cache_folder / './targets_mouse.pkl')
human_tracks = pd.read_pickle(cache_folder / './targets_human.pkl')


def search_tracks(keyword):
    """
    Helper function to search through available tracks.
    """
    m = mouse_tracks[mouse_tracks['description'].str.lower().str.contains(keyword.lower())]
    h = human_tracks[human_tracks['description'].str.lower().str.contains(keyword.lower())]
    cols = "index description".split()
    if len(m[cols]) > 0:
        print(f"## Mouse (total tracks: {mouse_tracks.shape[0]})")
        print(m[cols].head())
    if len(h[cols]) > 0:
        print(f"## Human (total tracks: {human_tracks.shape[0]})")
        print(h[cols].head())


    
def getseq(region='chr19:44,900,254-44,911,047', genome='hg19', length=196_608,
           silent=False):
    """
    Retrieve sequence from the UCSC genome browser
    
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
        
    seq = Sequence.get(genome = genome, chrom=chrom, start=new_start, end=new_stop)
    dna = seq.dna.upper()

    # save to cache - but only if we have write permissions:
    if os.access(dna_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(dna, F)

    return dna


PREP = False

if PREP:
    ENFORMER = from_pretrained('/mnt/storage/data/huggingface/hub/enformer', use_tf_gamma=True)
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



def run_enformer(sequence):

    # get hash
    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    # cache_file
    cache_file = enf_cache / f"{sha}.pkl.gz"    

    if cache_file.exists():
        print('Returning pre-cached enformer object')
        with gzip.open(cache_file, 'rb') as F:
            return pickle.load(F)
        
    print('Loading enformer into memory')
    enformer = from_pretrained('/mnt/storage/data/huggingface/hub/enformer', use_tf_gamma=True)

    print("Preparing tensor")
    tensor_seq = seq_indices_to_one_hot(str_to_seq_indices(sequence).unsqueeze(0))

    print('Execute enformer')
    output_seq = enformer(tensor_seq)

    print("Clean up memory")
    del enformer, tensor_seq
    print("Ready!")

    # save to cache - but only if we have write permissions:
    if os.access(enf_cache, os.W_OK):
        with gzip.open(cache_file, 'wb') as F:
            pickle.dump(output_seq, F)

    return output_seq


# easiest way to check if something happenend is by plotting
# so here is a plot helper function:
def trackplot(title, track, snp_pos):
    dat = pd.DataFrame(dict(y=track.detach().numpy()))
    dat['i'] = range(len(dat))
    dat['x'] = dat['i'] * 128 + snp_pos - 57344
    fig = plt.figure(figsize=(12,2))
    ax = plt.gca()
    dat.plot.scatter(x='x', y='y', s=8, c='k', ax=ax)
    midy = (dat['y'].max() - dat['y'].min()) / 2 + dat['y'].min()
    ax.axvline(snp_pos, zorder=-1, c='grey')
    ax.text(snp_pos, midy, ' snp', va='top')
    ax.axvline(139440238, zorder=-1, c='red', alpha=0.5)
    ax.text(139440238, midy, '<- NOTCH1 ', ha='right', va='top')
    plt.title(title)
