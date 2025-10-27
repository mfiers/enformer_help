#!/usr/bin/env python
"""
Quick test script to verify progress bar functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tqdm import tqdm
import time

def test_basic_progress():
    """Test basic tqdm progress bar."""
    print("Testing basic progress bar...")
    with tqdm(total=10, desc="Basic test", unit="item") as pbar:
        for i in range(10):
            time.sleep(0.2)
            pbar.update(1)
            pbar.set_postfix(count=i+1, status="ok")
    print("✓ Basic progress bar works!\n")


def test_nested_updates():
    """Test progress bar with nested operations."""
    print("Testing progress bar with nested operations...")
    stats = {'processed': 0, 'cached': 0, 'failed': 0}

    with tqdm(total=20, desc="Nested test", unit="item") as pbar:
        for i in range(20):
            # Simulate different outcomes
            if i % 3 == 0:
                stats['cached'] += 1
            elif i % 7 == 0:
                stats['failed'] += 1
            else:
                stats['processed'] += 1

            time.sleep(0.1)
            pbar.update(1)
            pbar.set_postfix(
                new=stats['processed'],
                cached=stats['cached'],
                failed=stats['failed']
            )

    print(f"✓ Nested updates work! Final: {stats}\n")


if __name__ == "__main__":
    print("="*60)
    print("Progress Bar Test Suite")
    print("="*60)
    print()

    try:
        test_basic_progress()
        test_nested_updates()

        print("="*60)
        print("All tests passed! ✓")
        print("="*60)

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
