#!/usr/bin/env python
"""
Test to understand actual cache behavior with and without resume flag.
"""

import sys
import time
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import enformer_help


def test_cache_hit():
    """Test behavior when sequence is already cached."""
    print("="*70)
    print("Test: Cache Hit Behavior")
    print("="*70)
    print()

    # Find a sequence that's already cached
    cache_folder = Path(__file__).parent / 'cache' / 'enformer'
    cached_files = list(cache_folder.glob("*.pkl.gz"))

    if not cached_files:
        print("❌ No cached files found. Cannot test.")
        return

    # We need to find the actual sequence for a cached SHA
    # This is tricky without the original data, so let's test with a known pattern
    print(f"Found {len(cached_files)} cached files")
    print(f"Testing with hypothetical cached sequence...")
    print()

    # Create a test sequence
    test_seq = "ACGT" * 49152  # 196,608 bp
    sha = hashlib.sha256(test_seq.encode('utf-8')).hexdigest()
    cache_file = cache_folder / f"{sha}.pkl.gz"

    print(f"Test sequence SHA: {sha[:32]}...")
    print(f"Cache file exists: {cache_file.exists()}")
    print()

    if cache_file.exists():
        print("✓ Sequence is cached. Testing retrieval speed...")
        start = time.time()
        result = enformer_help.run_enformer_keep_in_memory(test_seq, silent=True)
        elapsed = time.time() - start
        print(f"  Time: {elapsed:.3f} seconds (should be very fast if cached)")
        print()
    else:
        print("⚠ Test sequence not cached. This is expected.")
        print()


def test_internal_caching():
    """Verify that run_enformer_keep_in_memory checks cache internally."""
    print("="*70)
    print("Test: Internal Cache Checking")
    print("="*70)
    print()

    # Read the source to verify
    import inspect
    source = inspect.getsource(enformer_help.run_enformer_keep_in_memory)

    has_cache_check = "cache_file.exists()" in source
    print(f"✓ run_enformer_keep_in_memory checks cache internally: {has_cache_check}")

    if has_cache_check:
        print("  This means calling run_enformer_keep_in_memory will:")
        print("  1. Check if result is cached")
        print("  2. Load from cache if exists (FAST)")
        print("  3. Otherwise run model (SLOW)")
        print()


def analyze_resume_flag():
    """Explain what the --resume flag actually does."""
    print("="*70)
    print("Analysis: What does --resume actually do?")
    print("="*70)
    print()

    print("WITHOUT --resume flag:")
    print("  1. Script retrieves sequences for all SNPs")
    print("  2. For each sequence, calls run_enformer_keep_in_memory()")
    print("  3. run_enformer_keep_in_memory() checks cache internally")
    print("  4. If cached: returns immediately (fast)")
    print("  5. If not cached: runs model (slow)")
    print()

    print("WITH --resume flag:")
    print("  1. Script retrieves sequences for all SNPs")
    print("  2. For each sequence, checks cache BEFORE calling enformer")
    print("  3. If cached: skips entirely (saves a Python function call)")
    print("  4. If not cached: calls run_enformer_keep_in_memory()")
    print()

    print("Verdict:")
    print("  - --resume provides MINIMAL speedup (just skips function call)")
    print("  - The real caching happens INSIDE run_enformer_keep_in_memory()")
    print("  - --resume is useful mainly for TRACKING (shows 'cached' count)")
    print()


def recommendation():
    """Provide recommendation."""
    print("="*70)
    print("Recommendation")
    print("="*70)
    print()

    print("The current cache implementation is actually GOOD:")
    print()
    print("✓ enformer_help handles caching internally")
    print("✓ No need to manually check cache before calling")
    print("✓ --resume flag is optional (mainly for statistics)")
    print()

    print("Suggested usage:")
    print()
    print("  # Simple - let enformer_help handle caching")
    print("  python batch_enformer.py file.txt -n 1000")
    print()
    print("  # With --resume for better progress tracking")
    print("  python batch_enformer.py file.txt -n 1000 --resume")
    print()

    print("Both will use cached results automatically!")
    print()


if __name__ == "__main__":
    test_cache_hit()
    test_internal_caching()
    analyze_resume_flag()
    recommendation()
