#!/usr/bin/env python
"""
Verify that cache checking logic works correctly.
"""

import sys
import hashlib
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
import enformer_help


def check_cache_paths():
    """Verify cache paths match between script and module."""
    print("="*70)
    print("Cache Path Verification")
    print("="*70)
    print()

    # Get cache path from enformer_help module
    import enformer_help
    module_init = Path(enformer_help.__file__)
    module_cache = module_init.parent.parent / 'cache' / 'enformer'

    # Get cache path from script logic (what batch_enformer.py uses)
    script_cache = Path(__file__).parent / 'cache' / 'enformer'

    print(f"Module cache path: {module_cache}")
    print(f"Script cache path: {script_cache}")
    print(f"Paths match: {module_cache == script_cache}")
    print()

    print(f"Module cache exists: {module_cache.exists()}")
    print(f"Script cache exists: {script_cache.exists()}")
    print()

    if module_cache.exists():
        cached_files = list(module_cache.glob("*.pkl.gz"))
        print(f"Files in module cache: {len(cached_files)}")
        if cached_files:
            print(f"Example: {cached_files[0].name}")
    print()

    return module_cache, script_cache


def test_cache_detection():
    """Test if cache detection works with a real sequence."""
    print("="*70)
    print("Cache Detection Test")
    print("="*70)
    print()

    # Create a test sequence
    test_seq = "ACGT" * 49152  # 196,608 bp

    # Check hash
    sha = hashlib.sha256(test_seq.encode('utf-8')).hexdigest()
    print(f"Test sequence length: {len(test_seq)}")
    print(f"Test sequence SHA256: {sha}")
    print()

    # Check if cached using module's cache path
    module_cache = Path(enformer_help.__file__).parent.parent / 'cache' / 'enformer'
    cache_file = module_cache / f"{sha}.pkl.gz"

    print(f"Cache file path: {cache_file}")
    print(f"Cache file exists: {cache_file.exists()}")
    print()

    # Test the is_cached function from batch_enformer.py
    def is_cached_script(sequence):
        """Replicate batch_enformer.py logic."""
        cache_folder = Path(__file__).parent / 'cache'
        enf_cache = cache_folder / 'enformer'

        if not enf_cache.exists():
            return False

        sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
        cache_file = enf_cache / f"{sha}.pkl.gz"

        return cache_file.exists()

    cached = is_cached_script(test_seq)
    print(f"is_cached() result: {cached}")
    print()


def test_real_cache():
    """Check if there are any real cached results."""
    print("="*70)
    print("Real Cache Contents")
    print("="*70)
    print()

    cache_folder = Path(__file__).parent / 'cache' / 'enformer'

    if not cache_folder.exists():
        print(f"❌ Cache folder does not exist: {cache_folder}")
        print()
        return

    print(f"✓ Cache folder exists: {cache_folder}")

    # Count files
    cached_files = list(cache_folder.glob("*.pkl.gz"))
    print(f"Total cached files: {len(cached_files)}")
    print()

    if cached_files:
        print("Sample of cached files:")
        for i, f in enumerate(cached_files[:5]):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {i+1}. {f.name[:16]}... ({size_mb:.1f} MB)")
        print()

        # Test if we can detect one of these
        if len(cached_files) > 0:
            # Extract SHA from filename (remove .pkl.gz)
            example_sha = cached_files[0].stem.replace('.pkl', '')
            print(f"Testing detection with example SHA: {example_sha[:16]}...")

            # We don't have the sequence, but we can verify the file exists
            example_file = cache_folder / f"{example_sha}.pkl.gz"
            print(f"File exists: {example_file.exists()}")
            print()


def compare_with_enformer_help():
    """Compare with actual enformer_help internal cache checking."""
    print("="*70)
    print("Compare with enformer_help Internal Cache")
    print("="*70)
    print()

    # Get the cache path that enformer_help actually uses
    from enformer_help import enf_cache

    print(f"enformer_help.enf_cache: {enf_cache}")
    print(f"Exists: {enf_cache.exists()}")

    if enf_cache.exists():
        cached_files = list(enf_cache.glob("*.pkl.gz"))
        print(f"Files in enformer_help cache: {len(cached_files)}")
    print()

    # Compare with script logic
    script_cache = Path(__file__).parent / 'cache' / 'enformer'
    print(f"Script cache path: {script_cache}")
    print(f"Paths are identical: {enf_cache == script_cache}")
    print()


if __name__ == "__main__":
    try:
        check_cache_paths()
        test_cache_detection()
        test_real_cache()
        compare_with_enformer_help()

        print("="*70)
        print("Cache verification complete!")
        print("="*70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
