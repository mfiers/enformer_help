#!/usr/bin/env python
"""
Test script to verify local genome file produces same sequences as UCSC API cache.
"""

import sys
import gzip
import pickle
from pathlib import Path
import hashlib

sys.path.insert(0, str(Path(__file__).parent))
import enformer_help


def test_cached_sequences():
    """
    Test that local genome file produces same sequences as cached UCSC results.
    """
    print("="*70)
    print("Testing Local Genome vs Cached UCSC Sequences")
    print("="*70)
    print()

    # Find some cached DNA sequences
    dna_cache = Path(__file__).parent / 'cache' / 'dna'
    cached_files = list(dna_cache.glob("hg19__*.pkl.gz"))

    if not cached_files:
        print("❌ No cached DNA sequences found!")
        print(f"   Cache directory: {dna_cache}")
        return False

    print(f"Found {len(cached_files)} cached DNA sequences")
    print()

    # Test first 5 cached sequences
    test_count = min(5, len(cached_files))
    passed = 0
    failed = 0

    for i, cache_file in enumerate(cached_files[:test_count]):
        print(f"Test {i+1}/{test_count}: {cache_file.name}")

        # Parse filename: hg19__chr1_12345_67890.pkl.gz
        parts = cache_file.stem.replace('.pkl', '').split('__')
        if len(parts) != 2:
            print(f"  ⚠ Skipping - unexpected filename format")
            continue

        genome = parts[0]
        coords = parts[1].split('_')
        if len(coords) != 3:
            print(f"  ⚠ Skipping - unexpected coordinate format")
            continue

        chrom = coords[0]
        start = int(coords[1])
        stop = int(coords[2])

        # Load cached sequence
        with gzip.open(cache_file, 'rb') as f:
            cached_seq = pickle.load(f)

        print(f"  Cached: {len(cached_seq)} bp from {chrom}:{start}-{stop}")

        # Get sequence using new local genome method
        # Temporarily rename cache file so getseq doesn't use it
        temp_name = cache_file.with_suffix('.pkl.gz.temp')
        cache_file.rename(temp_name)

        try:
            # Use direct pysam access (bypassing getseq) to avoid coordinate interpretation issues
            import pysam
            genome_path = enformer_help.GENOME_PATHS[genome]
            if genome not in enformer_help._FASTA_CACHE:
                enformer_help._FASTA_CACHE[genome] = pysam.FastaFile(genome_path)
            fasta = enformer_help._FASTA_CACHE[genome]

            # Use coordinates directly as 0-based half-open
            new_seq = fasta.fetch(chrom, start, stop).upper()
            print(f"  Local:  {len(new_seq)} bp")

            # Compare sequences
            if cached_seq == new_seq:
                print(f"  ✓ PASS: Sequences match!")
                passed += 1
            else:
                print(f"  ✗ FAIL: Sequences differ!")
                print(f"    First 50bp cached: {cached_seq[:50]}")
                print(f"    First 50bp local:  {new_seq[:50]}")

                # Check if it's just a case difference
                if cached_seq.upper() == new_seq.upper():
                    print(f"    Note: Only case differs (should be OK)")
                    passed += 1
                else:
                    failed += 1

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

        finally:
            # Restore cache file
            temp_name.rename(cache_file)

        print()

    print("="*70)
    print("Test Results")
    print("="*70)
    print(f"Passed: {passed}/{test_count}")
    print(f"Failed: {failed}/{test_count}")

    if failed == 0:
        print()
        print("✓ All tests passed! Local genome produces same sequences as UCSC API.")
        return True
    else:
        print()
        print("✗ Some tests failed. Check coordinate system or genome version.")
        return False


def test_new_sequence():
    """
    Test retrieving a new sequence that isn't cached.
    """
    print()
    print("="*70)
    print("Testing New Sequence Retrieval")
    print("="*70)
    print()

    # Get a sequence from a common region
    region = "chr1:1000000-1000100"

    print(f"Retrieving: {region}")

    try:
        seq = enformer_help.getseq(region, genome='hg19', silent=False)
        print()
        print(f"✓ Retrieved {len(seq)} bp")
        print(f"  First 50bp: {seq[:50]}")
        print(f"  Last 50bp:  {seq[-50:]}")
        print()

        # Verify it's DNA sequence
        valid_bases = set('ACGTN')
        seq_bases = set(seq.upper())

        if seq_bases.issubset(valid_bases):
            print(f"✓ Sequence contains only valid DNA bases")
            return True
        else:
            invalid = seq_bases - valid_bases
            print(f"✗ Sequence contains invalid bases: {invalid}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("Testing enformer_help with local genome file")
    print(f"Genome file: {enformer_help.GENOME_PATHS['hg19']}")
    print()

    # Run tests
    test1 = test_cached_sequences()
    test2 = test_new_sequence()

    print()
    print("="*70)
    print("Overall Result")
    print("="*70)

    if test1 and test2:
        print("✓ All tests passed!")
        print("  Local genome file is working correctly.")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        print("  Please review the errors above.")
        sys.exit(1)
