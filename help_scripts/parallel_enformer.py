#!/usr/bin/env python
"""
Parallel Enformer execution script for processing large SNP datasets.

This script optimally parallelizes Enformer predictions across CPU cores,
using process pools for sequence retrieval and a single worker for model
execution to manage memory efficiently.

Strategy:
1. Use multiprocessing to parallelize sequence retrieval (CPU-bound, no memory issue)
2. Use a single persistent Enformer instance to process sequences (memory-intensive)
3. Leverage enformer_help's built-in caching to skip already-computed results
4. Adaptive batch sizing based on available CPU cores
"""

import argparse
import multiprocessing as mp
from multiprocessing import Pool, Queue, Manager
import sys
import time
from pathlib import Path
from typing import Iterator, Dict, Tuple, Optional
import signal

import torch
import pandas as pd
from tqdm import tqdm

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent))
import enformer_help


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Parallel Enformer prediction for large SNP datasets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "snp_file",
        type=str,
        help="Path to SNP file (e.g., Kunkle_etal_Stage1_results.txt)"
    )
    parser.add_argument(
        "-n", "--num-snps",
        type=int,
        default=None,
        help="Number of SNPs to process (default: all)"
    )
    parser.add_argument(
        "-s", "--skip",
        type=int,
        default=0,
        help="Number of SNPs to skip from start"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=None,
        help="Number of worker processes for sequence retrieval (default: CPU count - 1)"
    )
    parser.add_argument(
        "-b", "--batch-size",
        type=int,
        default=50,
        help="Batch size for sequence retrieval"
    )
    parser.add_argument(
        "--genome",
        type=str,
        default="hg19",
        help="Genome assembly to use"
    )
    parser.add_argument(
        "--length",
        type=int,
        default=196_608,
        help="Sequence length for Enformer"
    )
    parser.add_argument(
        "--filter-indels",
        action="store_true",
        help="Skip insertions and deletions (only process SNPs)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip SNPs that already have cached results"
    )

    return parser.parse_args()


def kunkle_reader(
    filename: str,
    skip: int = 0,
    num_snps: Optional[int] = None,
    filter_indels: bool = False
) -> Iterator[Dict]:
    """
    Generator that reads SNPs from Kunkle format file.

    Yields dictionaries with chr, pos, id, eff, neff, beta, se, p.
    """
    count = 0
    with open(filename) as F:
        # Skip header
        F.readline()

        # Skip requested number of lines
        for _ in range(skip):
            F.readline()

        for line in F:
            if num_snps is not None and count >= num_snps:
                break

            ls = line.strip().split()
            if len(ls) < 8:
                continue

            rec = {
                'chr': ls[0],
                'pos': ls[1],
                'id': ls[2],
                'eff': ls[3],
                'neff': ls[4],
                'beta': ls[5],
                'se': ls[6],
                'p': ls[7]
            }

            # Filter indels if requested
            if filter_indels:
                if len(rec['eff']) > 1 or len(rec['neff']) > 1:
                    continue

            count += 1
            yield rec


def get_sequences_for_snp(args: Tuple) -> Optional[Dict]:
    """
    Worker function to retrieve and prepare sequences for a SNP.

    This runs in parallel across multiple processes.
    Returns None if sequence preparation fails.
    """
    rec, genome, length = args

    try:
        FLEN = length
        halfway = (FLEN // 2) - 1

        pos = f"chr{rec['chr']}:{rec['pos']}-{rec['pos']}"
        seq = enformer_help.getseq(pos, genome=genome, length=FLEN, silent=True)

        # Determine which allele is in the reference
        if rec['neff'] == seq[halfway]:
            # Non-effect allele is reference
            nseq = seq
            fseq = seq[:halfway] + rec['eff'] + seq[halfway+1:]
        elif rec['eff'] == seq[halfway]:
            # Effect allele is reference
            fseq = seq
            nseq = seq[:halfway] + rec['neff'] + seq[halfway+1:]
        else:
            # Neither allele matches - skip this SNP
            return None

        # Ensure correct length
        def strim(s):
            if len(s) < FLEN:
                return None
            sta = (len(s) - FLEN) // 2
            return s[sta: sta+FLEN]

        if len(fseq) > FLEN:
            fseq = strim(fseq)
        if len(nseq) > FLEN:
            nseq = strim(nseq)

        if fseq is None or nseq is None:
            return None

        if len(nseq) != len(fseq) or len(nseq) != FLEN:
            return None

        return {
            'snp_id': (rec['chr'], rec['pos'], rec['id'], rec['eff'], rec['neff']),
            'fseq': fseq,
            'nseq': nseq,
            'metadata': rec
        }

    except Exception as e:
        # Silently skip problematic SNPs
        return None


def check_cache_exists(sequence: str) -> bool:
    """Check if a sequence already has cached Enformer results."""
    import hashlib
    import gzip

    cache_folder = Path(__file__).parent / 'cache'
    enf_cache = cache_folder / 'enformer'

    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    cache_file = enf_cache / f"{sha}.pkl.gz"

    return cache_file.exists()


def process_sequences_sequential(sequence_queue, results_queue, total, resume=False):
    """
    Sequential processor that runs Enformer on prepared sequences.

    This runs in a single process to manage memory efficiently.
    Keeps the Enformer model in memory for speed.
    """
    processed = 0
    skipped_cached = 0
    failed = 0

    pbar = tqdm(total=total, desc="Running Enformer", unit="SNP")

    try:
        while True:
            item = sequence_queue.get()

            if item is None:  # Poison pill
                break

            if item == "FAILED":
                failed += 1
                pbar.update(1)
                pbar.set_postfix(
                    processed=processed,
                    cached=skipped_cached,
                    failed=failed
                )
                continue

            snp_id = item['snp_id']
            fseq = item['fseq']
            nseq = item['nseq']

            try:
                # Check cache if resume mode
                if resume:
                    if check_cache_exists(fseq) and check_cache_exists(nseq):
                        skipped_cached += 1
                        pbar.update(1)
                        pbar.set_postfix(
                            processed=processed,
                            cached=skipped_cached,
                            failed=failed
                        )
                        continue

                # Run Enformer (uses caching internally)
                fenf = enformer_help.run_enformer_keep_in_memory(fseq, silent=True)
                nenf = enformer_help.run_enformer_keep_in_memory(nseq, silent=True)

                processed += 1
                pbar.update(1)
                pbar.set_postfix(
                    processed=processed,
                    cached=skipped_cached,
                    failed=failed
                )

                # Optional: store results in results_queue for further processing
                # results_queue.put({'snp_id': snp_id, 'fenf': fenf, 'nenf': nenf})

            except Exception as e:
                failed += 1
                pbar.update(1)
                pbar.set_postfix(
                    processed=processed,
                    cached=skipped_cached,
                    failed=failed
                )

    finally:
        pbar.close()
        results_queue.put({
            'processed': processed,
            'skipped_cached': skipped_cached,
            'failed': failed
        })


def main():
    """Main execution function."""
    args = parse_args()

    # Determine number of workers
    cpu_count = mp.cpu_count()
    if args.workers is None:
        # Reserve 1 CPU for Enformer, rest for sequence retrieval
        args.workers = max(1, cpu_count - 1)

    print(f"Configuration:")
    print(f"  SNP file: {args.snp_file}")
    print(f"  Number of SNPs: {args.num_snps or 'all'}")
    print(f"  Skip: {args.skip}")
    print(f"  Workers: {args.workers}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Genome: {args.genome}")
    print(f"  Filter indels: {args.filter_indels}")
    print(f"  Resume mode: {args.resume}")
    print(f"  Available CPUs: {cpu_count}")
    print()

    # Create queues for inter-process communication
    manager = Manager()
    sequence_queue = manager.Queue(maxsize=args.batch_size * 2)
    results_queue = manager.Queue()

    # Count total SNPs for progress bar
    print("Counting SNPs...")
    total_snps = sum(1 for _ in kunkle_reader(
        args.snp_file,
        skip=args.skip,
        num_snps=args.num_snps,
        filter_indels=args.filter_indels
    ))
    print(f"Processing {total_snps} SNPs")
    print()

    # Start the Enformer processor in a separate process
    enformer_process = mp.Process(
        target=process_sequences_sequential,
        args=(sequence_queue, results_queue, total_snps, args.resume)
    )
    enformer_process.start()

    # Process SNPs in batches with parallel sequence retrieval
    start_time = time.time()

    try:
        with Pool(processes=args.workers) as pool:
            snp_generator = kunkle_reader(
                args.snp_file,
                skip=args.skip,
                num_snps=args.num_snps,
                filter_indels=args.filter_indels
            )

            # Prepare arguments for parallel processing
            task_args = ((rec, args.genome, args.length) for rec in snp_generator)

            # Process in batches
            for result in pool.imap_unordered(
                get_sequences_for_snp,
                task_args,
                chunksize=args.batch_size
            ):
                if result is None:
                    sequence_queue.put("FAILED")
                else:
                    sequence_queue.put(result)

        # Send poison pill to stop Enformer processor
        sequence_queue.put(None)

        # Wait for Enformer processor to finish
        enformer_process.join()

    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
        enformer_process.terminate()
        enformer_process.join()
        sys.exit(1)

    # Get final statistics
    final_stats = results_queue.get()

    elapsed = time.time() - start_time
    print()
    print("="*60)
    print("Final Statistics:")
    print(f"  Total SNPs attempted: {total_snps}")
    print(f"  Successfully processed: {final_stats['processed']}")
    print(f"  Skipped (cached): {final_stats['skipped_cached']}")
    print(f"  Failed: {final_stats['failed']}")
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"  Rate: {final_stats['processed']/elapsed:.2f} SNPs/second")
    print("="*60)


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
