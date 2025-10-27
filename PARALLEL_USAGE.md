# Parallel Enformer Processing Guide

This guide explains how to efficiently process large SNP datasets with Enformer using the provided parallelization scripts.

## Overview

Two scripts are provided for parallel Enformer execution:

1. **`batch_enformer.py`** - Simpler, more memory-efficient (RECOMMENDED)
2. **`parallel_enformer.py`** - Advanced multi-process architecture

Both scripts:
- Parallelize sequence retrieval from UCSC (I/O and CPU bound)
- Keep Enformer model in memory for faster execution
- Leverage built-in caching (skip already-computed sequences)
- Provide progress tracking and statistics

## Quick Start

### Basic Usage

Process first 1000 SNPs:
```bash
python batch_enformer.py /data/user/u0089478/enformer/Kunkle_etal_Stage1_results.txt -n 1000
```

Process with resume capability (skip cached):
```bash
python batch_enformer.py /data/user/u0089478/enformer/Kunkle_etal_Stage1_results.txt --resume
```

Process all SNPs (11.4M - will take days):
```bash
python batch_enformer.py /data/user/u0089478/enformer/Kunkle_etal_Stage1_results.txt
```

### Advanced Options

```bash
# Skip first 10000 SNPs, process next 5000
python batch_enformer.py Kunkle_etal_Stage1_results.txt -s 10000 -n 5000

# Use 8 workers for sequence retrieval
python batch_enformer.py Kunkle_etal_Stage1_results.txt -w 8

# Filter out insertions/deletions (only SNPs)
python batch_enformer.py Kunkle_etal_Stage1_results.txt --filter-indels

# Use different genome assembly
python batch_enformer.py Kunkle_etal_Stage1_results.txt --genome hg38
```

## Script Comparison

### batch_enformer.py (RECOMMENDED)

**Pros:**
- Simpler architecture, easier to debug
- Better memory management
- Automatic chunk-based processing
- More predictable behavior

**Cons:**
- Slightly less optimal parallelization

**Best for:** Most use cases, especially on systems with limited memory

### parallel_enformer.py

**Pros:**
- More sophisticated multi-process architecture
- Separate queue-based processing pipeline
- Potentially faster on high-core systems

**Cons:**
- More complex, harder to debug
- Higher memory overhead
- Queue management overhead

**Best for:** High-performance computing clusters with many cores

## Performance Considerations

### Parallelization Strategy

The scripts use a two-stage parallelization approach:

1. **Stage 1: Sequence Retrieval (Parallel)**
   - Multiple workers fetch sequences from UCSC API
   - Parse and prepare effect/non-effect variants
   - CPU and I/O bound

2. **Stage 2: Enformer Execution (Sequential)**
   - Single Enformer instance kept in memory
   - Processes sequences sequentially
   - Memory bound (Enformer model is large)

**Why not parallelize Enformer execution?**
- Each Enformer instance requires ~4-8GB RAM
- CPU-only inference is relatively slow
- Better to keep one instance in memory and process sequentially
- Parallelizing would cause memory thrashing

### Expected Performance

Rough estimates (CPU-only, no GPU):

- **Sequence retrieval:** ~50-100 SNPs/second (parallel)
- **Enformer inference:** ~5-10 seconds per sequence
- **Overall rate:** ~0.05-0.1 SNPs/second (bottlenecked by Enformer)

For 11.4M SNPs:
- **Without caching:** ~1.3-2.6 years of compute time
- **With 90% cached:** ~47-95 days
- **With 99% cached:** ~4.7-9.5 days

### Optimization Tips

1. **Use Resume Mode**: Always use `--resume` to skip cached results
   ```bash
   python batch_enformer.py file.txt --resume
   ```

2. **Process in Chunks**: For very large datasets, process in chunks
   ```bash
   # Process first 10k
   python batch_enformer.py file.txt -n 10000
   # Then next 10k
   python batch_enformer.py file.txt -s 10000 -n 10000
   ```

3. **Filter Indels**: If you only need SNPs, filter indels
   ```bash
   python batch_enformer.py file.txt --filter-indels
   ```

4. **Monitor System Resources**:
   ```bash
   # In another terminal
   htop
   # or
   watch -n 1 'ps aux | grep enformer'
   ```

5. **Use Screen/Tmux**: For long-running jobs
   ```bash
   screen -S enformer
   python batch_enformer.py file.txt
   # Ctrl+A, D to detach
   # screen -r enformer to reattach
   ```

## Understanding the Cache

Both scripts leverage `enformer_help`'s built-in caching:

### Cache Location
```
cache/
├── dna/              # DNA sequences from UCSC
│   └── hg19__chr1_12345_67890.pkl.gz
└── enformer/         # Enformer predictions
    └── abc123...def.pkl.gz  # SHA256 hash of sequence
```

### Cache Benefits
- **DNA sequences**: Skip repeated UCSC API calls
- **Enformer results**: Skip expensive model inference
- **Automatic**: No manual cache management needed
- **Persistent**: Results survive script restarts

### Cache Size
- Each DNA sequence: ~200KB compressed
- Each Enformer result: ~50-100MB compressed
- 10,000 SNPs: ~1-2TB cache size

## Monitoring Progress

Both scripts provide real-time progress bars:

```
Processing: 45%|████████     | 4532/10000 [1:23:45<2:15:12, 0.67SNP/s]
{new: 325, cached: 4187, failed: 20}
```

Where:
- **new**: Newly computed Enformer predictions
- **cached**: Skipped (already in cache)
- **failed**: Sequence retrieval or processing failures

## Error Handling

The scripts handle errors gracefully:

- **Missing sequences**: Skipped (e.g., chromosome not in genome)
- **Allele mismatches**: Skipped (reference doesn't match either allele)
- **Keyboard interrupt**: Clean shutdown with statistics
- **Individual failures**: Logged but don't stop processing

## Full Command Reference

### batch_enformer.py

```
usage: batch_enformer.py [-h] [-n NUM_SNPS] [-s SKIP] [-w SEQ_WORKERS]
                         [--genome GENOME] [--filter-indels] [--resume]
                         [--checkpoint-interval CHECKPOINT_INTERVAL]
                         snp_file

Arguments:
  snp_file              Path to SNP file
  -n, --num-snps        Number of SNPs to process (default: all)
  -s, --skip            Skip first N SNPs (default: 0)
  -w, --seq-workers     Workers for sequence retrieval (default: CPU-2)
  --genome              Genome assembly (default: hg19)
  --filter-indels       Skip insertions/deletions
  --resume              Skip already cached results
  --checkpoint-interval Print progress every N SNPs (default: 100)
```

### parallel_enformer.py

```
usage: parallel_enformer.py [-h] [-n NUM_SNPS] [-s SKIP] [-w WORKERS]
                            [-b BATCH_SIZE] [--genome GENOME]
                            [--filter-indels] [--resume]
                            snp_file

Arguments:
  snp_file              Path to SNP file
  -n, --num-snps        Number of SNPs to process (default: all)
  -s, --skip            Skip first N SNPs (default: 0)
  -w, --workers         Worker processes for retrieval (default: CPU-1)
  -b, --batch-size      Batch size for retrieval (default: 50)
  --genome              Genome assembly (default: hg19)
  --filter-indels       Skip insertions/deletions
  --resume              Skip already cached results
```

## Example Workflow

### Process dataset in stages

```bash
# Stage 1: Test with small sample
python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 100

# Stage 2: Process first 10k
python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 10000

# Stage 3: Resume processing (skip cached)
python batch_enformer.py Kunkle_etal_Stage1_results.txt --resume

# Stage 4: Check what's left
python -c "
import hashlib
from pathlib import Path
cache = Path('cache/enformer')
print(f'Cached results: {len(list(cache.glob(\"*.pkl.gz\")))}')
"
```

## Troubleshooting

### Out of Memory
- Reduce sequence workers: `-w 2`
- Process smaller chunks: `-n 1000`
- Monitor with `htop`

### Slow Performance
- Check network (UCSC API)
- Verify cache directory is writable
- Consider filtering indels: `--filter-indels`

### Hanging
- Check for disk space (cache can be large)
- Kill and restart with `--resume`

### Cache Issues
- Cache location: `./cache/enformer/`
- Verify write permissions: `ls -la cache/`
- Clear cache if corrupted: `rm -rf cache/enformer/*.pkl.gz`

## Post-Processing

After caching Enformer results, use the original notebook for analysis:

```python
# The cached results can be accessed via enformer_help
import enformer_help

# Load a specific sequence result
result = enformer_help.run_enformer(sequence)  # Loads from cache if exists

# Or use run_enformer_keep_in_memory for batch analysis
result = enformer_help.run_enformer_keep_in_memory(sequence, silent=True)
```

## Questions?

For issues or questions about the parallelization scripts, please open an issue on the repository.
