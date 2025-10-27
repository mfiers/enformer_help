#!/usr/bin/env python
"""
Debug script to understand UCSC vs pysam coordinate systems.
"""

import sys
import gzip
import pickle
from pathlib import Path
import pysam

sys.path.insert(0, str(Path(__file__).parent))


def test_coordinate_system():
    """Test different coordinate interpretations."""

    # Get a cached sequence
    dna_cache = Path(__file__).parent / 'cache' / 'dna'
    cached_files = list(dna_cache.glob("hg19__chr*.pkl.gz"))

    if not cached_files:
        print("No cached files found")
        return

    cache_file = cached_files[0]
    print(f"Testing with: {cache_file.name}")
    print()

    # Parse filename
    parts = cache_file.stem.replace('.pkl', '').split('__')
    coords = parts[1].split('_')
    chrom = coords[0]
    start = int(coords[1])
    stop = int(coords[2])

    # Load cached sequence
    with gzip.open(cache_file, 'rb') as f:
        cached_seq = pickle.load(f)

    print(f"Chromosome: {chrom}")
    print(f"Cached coordinates: {start}-{stop}")
    print(f"Cached length: {len(cached_seq)}")
    print(f"Cached first 100bp: {cached_seq[:100]}")
    print()

    # Open genome file
    genome_path = '/data/db/genomes/hg19/fasta/hg19.fa'
    fasta = pysam.FastaFile(genome_path)

    # Try different coordinate interpretations
    print("="*70)
    print("Testing different coordinate interpretations:")
    print("="*70)
    print()

    # 1. UCSC 1-based inclusive both ends
    print("1. UCSC format (1-based inclusive): start-1 to stop")
    seq1 = fasta.fetch(chrom, start-1, stop).upper()
    print(f"   Length: {len(seq1)}")
    print(f"   First 100bp: {seq1[:100]}")
    print(f"   Match: {seq1 == cached_seq}")
    print()

    # 2. 0-based half-open as-is
    print("2. Direct 0-based half-open: start to stop")
    seq2 = fasta.fetch(chrom, start, stop).upper()
    print(f"   Length: {len(seq2)}")
    print(f"   First 100bp: {seq2[:100]}")
    print(f"   Match: {seq2 == cached_seq}")
    print()

    # 3. start-1 to start-1+length
    length = len(cached_seq)
    print(f"3. Using length ({length}): start-1 to start-1+length")
    seq3 = fasta.fetch(chrom, start-1, start-1+length).upper()
    print(f"   Length: {len(seq3)}")
    print(f"   First 100bp: {seq3[:100]}")
    print(f"   Match: {seq3 == cached_seq}")
    print()

    # 4. Check if it's 1-based exclusive on end
    print("4. 1-based start, exclusive end: start-1 to stop-1")
    seq4 = fasta.fetch(chrom, start-1, stop-1).upper()
    print(f"   Length: {len(seq4)}")
    print(f"   First 100bp: {seq4[:100]}")
    print(f"   Match: {seq4 == cached_seq}")
    print()

    # Check reverse complement (in case of strand issues)
    def reverse_complement(seq):
        comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
        return ''.join(comp.get(b, b) for b in reversed(seq))

    print("5. Checking reverse complement of option 1:")
    seq1_rc = reverse_complement(seq1)
    print(f"   Match: {seq1_rc == cached_seq}")
    print()


if __name__ == "__main__":
    test_coordinate_system()
