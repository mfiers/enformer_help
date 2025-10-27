#!/usr/bin/env python
"""
Adaptive batch Enformer execution script for maximum throughput.

This script uses a simpler architecture optimized for CPU-only systems:
- Parallel sequence retrieval (I/O and CPU bound)
- Single Enformer instance kept in memory
- Adaptive memory management
- Smart caching with resume capability

Usage:
    python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 10000
    python batch_enformer.py Kunkle_etal_Stage1_results.txt --resume
"""

import argparse
import sys
import time
import hashlib
import gzip
import pickle
from pathlib import Path
from typing import Iterator, Dict, Optional, List
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
import enformer_help


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch Enformer prediction with adaptive parallelization",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "snp_file",
        type=str,
        help="Path to SNP file"
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
        help="Skip first N SNPs"
    )
    parser.add_argument(
        "-w", "--seq-workers",
        type=int,
        default=None,
        help="Workers for sequence retrieval (default: CPU count - 2)"
    )
    parser.add_argument(
        "--genome",
        type=str,
        default="hg19",
        help="Genome assembly"
    )
    parser.add_argument(
        "--filter-indels",
        action="store_true",
        help="Skip insertions/deletions"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip already cached results"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=100,
        help="Print progress every N SNPs"
    )
    parser.add_argument(
        "--negative-control",
        type=int,
        default=None,
        help="Add negative control at position +N bp (e.g., 5000 for 5kb upstream)"
    )

    return parser.parse_args()


def read_snps(
    filename: str,
    skip: int = 0,
    num_snps: Optional[int] = None,
    filter_indels: bool = False
) -> Iterator[Dict]:
    """Read SNPs from file."""
    count = 0
    with open(filename) as F:
        F.readline()  # Skip header

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
                'neff': ls[4]
            }

            # Filter indels
            if filter_indels and (len(rec['eff']) > 1 or len(rec['neff']) > 1):
                continue

            count += 1
            yield rec


def get_sequence_pair(args) -> Optional[Dict]:
    """
    Get effect and non-effect sequences for a SNP.
    Optionally includes negative control at offset position.
    Runs in parallel worker processes.
    """
    rec, genome, control_offset = args

    try:
        FLEN = 196_608
        halfway = (FLEN // 2) - 1

        # Get main SNP position
        pos = f"chr{rec['chr']}:{rec['pos']}-{rec['pos']}"
        seq = enformer_help.getseq(pos, genome=genome, length=FLEN, silent=True)

        # Check which allele matches reference
        if rec['neff'] == seq[halfway]:
            nseq = seq
            fseq = seq[:halfway] + rec['eff'] + seq[halfway+1:]
        elif rec['eff'] == seq[halfway]:
            fseq = seq
            nseq = seq[:halfway] + rec['neff'] + seq[halfway+1:]
        else:
            return None

        # Trim to exact length
        def trim_seq(s):
            if len(s) < FLEN:
                return None
            if len(s) > FLEN:
                start = (len(s) - FLEN) // 2
                s = s[start:start+FLEN]
            return s

        fseq = trim_seq(fseq)
        nseq = trim_seq(nseq)

        if fseq is None or nseq is None or len(fseq) != FLEN or len(nseq) != FLEN:
            return None

        snp_id = (rec['chr'], rec['pos'], rec['id'], rec['eff'], rec['neff'])

        result = {
            'snp_id': snp_id,
            'fseq': fseq,
            'nseq': nseq
        }

        # Add negative control if requested
        if control_offset is not None:
            control_pos = int(rec['pos']) + control_offset
            control_pos_str = f"chr{rec['chr']}:{control_pos}-{control_pos}"

            try:
                control_seq = enformer_help.getseq(control_pos_str, genome=genome, length=FLEN, silent=True)

                # Get the reference allele at control position
                control_ref = control_seq[halfway]

                # Create control sequences by inserting the same alleles as the SNP
                # Control "effect": insert effect allele at control position
                control_fseq = control_seq[:halfway] + rec['eff'] + control_seq[halfway+1:]
                # Control "non-effect": insert non-effect allele at control position
                control_nseq = control_seq[:halfway] + rec['neff'] + control_seq[halfway+1:]

                control_fseq = trim_seq(control_fseq)
                control_nseq = trim_seq(control_nseq)

                if control_fseq is not None and control_nseq is not None:
                    control_id = (rec['chr'], str(control_pos), f"{rec['id']}_control", rec['eff'], rec['neff'])
                    result['control'] = {
                        'snp_id': control_id,
                        'fseq': control_fseq,
                        'nseq': control_nseq,
                        'ref_allele': control_ref
                    }
            except Exception:
                # If control sequence retrieval fails, just skip the control
                pass

        return result

    except Exception:
        return None


def is_cached(sequence: str) -> bool:
    """Check if sequence result is already cached."""
    cache_folder = Path(__file__).parent / 'cache'
    enf_cache = cache_folder / 'enformer'

    if not enf_cache.exists():
        return False

    sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
    cache_file = enf_cache / f"{sha}.pkl.gz"

    return cache_file.exists()


class EnformerRunner:
    """
    Singleton Enformer runner that keeps model in memory.
    """

    def __init__(self, output_vcf=None):
        self.stats = {
            'processed': 0,
            'cached': 0,
            'failed': 0,
            'controls_processed': 0,
            'controls_cached': 0,
            'controls_failed': 0
        }
        self.output_vcf = output_vcf
        if output_vcf:
            # Initialize VCF file with header
            self._init_vcf()

    def _init_vcf(self):
        """Initialize VCF file with header."""
        with open(self.output_vcf, 'w') as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("##source=enformer_batch_processor\n")
            f.write("##INFO=<ID=TYPE,Number=1,Type=String,Description=\"SNP or CONTROL\">\n")
            f.write("##INFO=<ID=ORIGINAL_SNP,Number=1,Type=String,Description=\"Original SNP ID for controls\">\n")
            f.write("##INFO=<ID=REF_ALLELE,Number=1,Type=String,Description=\"Reference allele at this position\">\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")

    def _write_vcf_record(self, snp_id, is_control=False, original_snp=None, ref_allele=None):
        """Write a VCF record."""
        if not self.output_vcf:
            return

        chrom, pos, snp_name, eff, neff = snp_id

        # Determine REF and ALT
        if ref_allele:
            ref = ref_allele
            alt = f"{eff},{neff}"
        else:
            # For main SNP, we don't know which is ref without checking
            ref = neff
            alt = eff

        # Build INFO field
        info_parts = []
        if is_control:
            info_parts.append("TYPE=CONTROL")
            if original_snp:
                info_parts.append(f"ORIGINAL_SNP={original_snp}")
        else:
            info_parts.append("TYPE=SNP")

        if ref_allele:
            info_parts.append(f"REF_ALLELE={ref_allele}")

        info = ";".join(info_parts) if info_parts else "."

        # Write record
        with open(self.output_vcf, 'a') as f:
            f.write(f"{chrom}\t{pos}\t{snp_name}\t{ref}\t{alt}\t.\t.\t{info}\n")

    def run(self, seq_pairs: List[Dict], resume: bool = False, pbar=None) -> None:
        """
        Run Enformer on a batch of sequence pairs.

        Args:
            seq_pairs: List of dicts with 'snp_id', 'fseq', 'nseq'
            resume: Skip if already cached
            pbar: Progress bar to update
        """
        for pair in seq_pairs:
            if pair is None:
                self.stats['failed'] += 1
                if pbar:
                    pbar.update(1)
                    pbar.set_postfix(
                        computed=self.stats['processed'],
                        cached=self.stats['cached'],
                        failed=self.stats['failed']
                    )
                continue

            try:
                fseq = pair['fseq']
                nseq = pair['nseq']
                snp_id = pair['snp_id']

                # Check if both sequences are already cached
                fseq_cached = is_cached(fseq)
                nseq_cached = is_cached(nseq)
                both_cached = fseq_cached and nseq_cached

                # If resume mode and both cached, skip the function call entirely
                if resume and both_cached:
                    self.stats['cached'] += 1
                else:
                    # Run Enformer (uses internal caching)
                    enformer_help.run_enformer_keep_in_memory(fseq, silent=True)
                    enformer_help.run_enformer_keep_in_memory(nseq, silent=True)

                    # Track based on whether we actually computed or loaded from cache
                    if both_cached:
                        self.stats['cached'] += 1
                    else:
                        self.stats['processed'] += 1

                # Write main SNP to VCF if requested
                self._write_vcf_record(snp_id, is_control=False)

                # Process control if present
                if 'control' in pair:
                    control = pair['control']
                    try:
                        control_fseq = control['fseq']
                        control_nseq = control['nseq']
                        control_id = control['snp_id']
                        control_ref = control.get('ref_allele')

                        # Check control cache
                        control_fseq_cached = is_cached(control_fseq)
                        control_nseq_cached = is_cached(control_nseq)
                        control_both_cached = control_fseq_cached and control_nseq_cached

                        if resume and control_both_cached:
                            self.stats['controls_cached'] += 1
                        else:
                            # Run Enformer on control
                            enformer_help.run_enformer_keep_in_memory(control_fseq, silent=True)
                            enformer_help.run_enformer_keep_in_memory(control_nseq, silent=True)

                            if control_both_cached:
                                self.stats['controls_cached'] += 1
                            else:
                                self.stats['controls_processed'] += 1

                        # Write control to VCF
                        self._write_vcf_record(
                            control_id,
                            is_control=True,
                            original_snp=snp_id[2],  # Original SNP ID
                            ref_allele=control_ref
                        )

                    except Exception:
                        self.stats['controls_failed'] += 1

                if pbar:
                    pbar.update(1)
                    pbar.set_postfix(
                        snp_new=self.stats['processed'],
                        snp_cache=self.stats['cached'],
                        ctrl_new=self.stats['controls_processed'],
                        failed=self.stats['failed']
                    )

            except Exception:
                self.stats['failed'] += 1
                if pbar:
                    pbar.update(1)
                    pbar.set_postfix(
                        snp_new=self.stats['processed'],
                        snp_cache=self.stats['cached'],
                        ctrl_new=self.stats['controls_processed'],
                        failed=self.stats['failed']
                    )

    def get_stats(self) -> Dict:
        """Get processing statistics."""
        return self.stats.copy()


def main():
    """Main execution."""
    args = parse_args()

    # Configure workers
    cpu_count = mp.cpu_count()
    if args.seq_workers is None:
        # Reserve CPUs for Enformer process + main thread
        args.seq_workers = max(1, cpu_count - 2)

    print("="*70)
    print("Batch Enformer Processor")
    print("="*70)
    print(f"SNP file:             {args.snp_file}")
    print(f"Number of SNPs:       {args.num_snps or 'all'}")
    print(f"Skip:                 {args.skip}")
    print(f"Genome:               {args.genome}")
    print(f"Sequence workers:     {args.seq_workers}")
    print(f"Filter indels:        {args.filter_indels}")
    print(f"Resume mode:          {args.resume}")
    print(f"Negative control:     {args.negative_control or 'disabled'}")
    if args.negative_control:
        print(f"  Control offset:     +{args.negative_control} bp")
    print(f"Available CPUs:       {cpu_count}")
    print("="*70)
    print()

    # Prepare VCF output if controls are requested
    output_vcf = None
    if args.negative_control:
        output_vcf = f"controls_{Path(args.snp_file).stem}.vcf"
        print(f"Control VCF output: {output_vcf}")
        print()

    # Initialize Enformer runner
    runner = EnformerRunner(output_vcf=output_vcf)

    # Read SNPs
    print("Loading SNPs...")
    snps = list(read_snps(
        args.snp_file,
        skip=args.skip,
        num_snps=args.num_snps,
        filter_indels=args.filter_indels
    ))
    total = len(snps)
    print(f"Total SNPs to process: {total:,}")
    print()

    # Process with parallel sequence retrieval
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=args.seq_workers) as executor:
        # Prepare tasks - include control_offset
        tasks = [(snp, args.genome, args.negative_control) for snp in snps]

        # Process with progress bar
        with tqdm(total=total, desc="Processing", unit="SNP") as pbar:
            # Submit in chunks to manage memory
            chunk_size = args.seq_workers * 10
            batch = []

            for result in executor.map(get_sequence_pair, tasks, chunksize=10):
                batch.append(result)

                # Process batch when it reaches chunk_size
                if len(batch) >= chunk_size:
                    runner.run(batch, resume=args.resume, pbar=pbar)
                    batch = []

            # Process remaining batch
            if batch:
                runner.run(batch, resume=args.resume, pbar=pbar)

    # Final statistics
    elapsed = time.time() - start_time
    stats = runner.get_stats()

    print()
    print("="*70)
    print("FINAL STATISTICS")
    print("="*70)
    print(f"Total SNPs:                     {total:,}")
    print()
    print("Main SNPs:")
    print(f"  Newly computed:               {stats['processed']:,} (ran model)")
    print(f"  Loaded from cache:            {stats['cached']:,} (already computed)")
    print(f"  Failed:                       {stats['failed']:,}")

    if args.negative_control:
        print()
        print("Negative Controls:")
        print(f"  Newly computed:               {stats['controls_processed']:,}")
        print(f"  Loaded from cache:            {stats['controls_cached']:,}")
        print(f"  Failed:                       {stats['controls_failed']:,}")
        print()
        print(f"Control VCF output:             {output_vcf}")

    print()
    print(f"Total time:                     {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    successful = stats['processed'] + stats['cached']
    if successful > 0:
        print(f"Overall SNP rate:               {successful/elapsed:.2f} SNPs/second")
    if stats['processed'] > 0:
        print(f"New computation rate:           {stats['processed']/elapsed:.2f} SNPs/second")
        print(f"Time per new SNP:               {elapsed/stats['processed']:.2f} seconds")

    if args.negative_control:
        total_controls = stats['controls_processed'] + stats['controls_cached']
        if total_controls > 0:
            print(f"Total controls processed:       {total_controls:,}")

    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
