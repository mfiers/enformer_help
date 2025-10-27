# EnformerHelp Quick Reference

## Installation

```bash
cd /data/teachers/software/enformer_help
pip install -e .
```

## Import (IMPORTANT!)

```python
# ✅ CORRECT
import enformer_help

# ❌ WRONG
import enformerhelp
```

## Basic Usage

### Get DNA Sequence
```python
import enformer_help

seq = enformer_help.getseq(
    region='chr1:1000000-1000100',
    genome='hg19'
)
```

### Run Enformer
```python
# Automatically uses cache if available
result = enformer_help.run_enformer(seq)

# Access predictions
human_predictions = result['human']
mouse_predictions = result['mouse']
```

### Search Tracks
```python
enformer_help.search_tracks('dnase')
```

### Plot Results
```python
enformer_help.trackplot(
    title="Track name",
    track=result['human'][0, :, 123],
    snp_pos=1000000
)
```

## Batch Processing

### Process SNPs with Controls

```bash
# Process 1000 SNPs with 5kb controls
python batch_enformer.py \
    Kunkle_etal_Stage1_results_sorted_pvalue.txt \
    -n 1000 \
    --negative-control 5000
```

### Resume Processing

```bash
# Continue from where you left off
python batch_enformer.py \
    input_file.txt \
    --resume \
    --negative-control 5000
```

## File Locations

### Package
```
/data/teachers/software/enformer_help/
```

### Genomes
```
/data/db/genomes/hg19/fasta/hg19.fa
/data/db/genomes/hg19/fasta/hg19.fa.fai  (index)
```

### Cache
```
/data/teachers/software/enformer_help/cache/
├── dna/          # DNA sequences
├── enformer/     # Enformer predictions
└── hub/          # Enformer model weights
```

### SNP Data
```
# Original (position-ordered)
/data/user/u0089478/enformer/Kunkle_etal_Stage1_results.txt

# Sorted (p-value-ordered, most significant first)
/data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt
```

## Scripts

### Batch Processing
```bash
/data/teachers/software/enformer_help/batch_enformer.py
```

### Sort SNPs by P-value
```bash
/data/teachers/software/enformer_help/sort_kunkle_by_pvalue.py
```

### Test Installation
```bash
/data/teachers/software/enformer_help/test_local_genome.py
/data/teachers/software/enformer_help/verify_cache.py
```

## Common Commands

### Test Import
```bash
python -c "import enformer_help; print('✓ Works!')"
```

### Check Cache
```bash
ls cache/enformer/*.pkl.gz | wc -l
du -sh cache/enformer/
```

### Process Top 100 SNPs
```bash
python batch_enformer.py \
    /data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt \
    -n 100 \
    --negative-control 5000
```

### Sort Custom SNP File
```bash
python sort_kunkle_by_pvalue.py my_snps.txt
```

## Key Parameters

### batch_enformer.py

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-n, --num-snps` | all | Number of SNPs to process |
| `-s, --skip` | 0 | Skip first N SNPs |
| `-w, --seq-workers` | CPU-2 | Parallel workers |
| `--genome` | hg19 | Genome assembly |
| `--negative-control` | None | Control offset (bp) |
| `--resume` | False | Skip cached results |
| `--filter-indels` | False | Only process SNPs |

## Output Files

### VCF (with controls)
```
controls_<input_filename>.vcf
```

Contains main SNPs and control positions.

## Documentation

| File | Description |
|------|-------------|
| `README.md` | Overview and quick start |
| `INSTALL.md` | Detailed installation |
| `LOCAL_GENOME_SETUP.md` | Genome file setup |
| `PARALLEL_USAGE.md` | Batch processing guide |
| `NEGATIVE_CONTROLS.md` | Control feature details |
| `CACHE_EXPLAINED.md` | Caching behavior |
| `SORTED_SNP_FILE.md` | Sorted file usage |

## Troubleshooting

### Import fails
```bash
# Check installation
pip list | grep enformer

# Reinstall
cd /data/teachers/software/enformer_help
pip install -e .
```

### Wrong import name
```python
# Use underscore!
import enformer_help  # ✅
import enformerhelp   # ❌
```

### Genome not found
```python
# Check paths in enformer_help/__init__.py
import enformer_help
print(enformer_help.GENOME_PATHS)
```

### Cache issues
```bash
# Check cache directory
ls -lh cache/enformer/ | head

# Verify cache
python verify_cache.py
```

## Quick Examples

### Example 1: Process Most Significant SNPs
```bash
python batch_enformer.py \
    /data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt \
    -n 1000 \
    --negative-control 5000 \
    --resume
```

### Example 2: Test Single SNP
```python
import enformer_help

# Get sequence for rs12972156 (top SNP)
seq = enformer_help.getseq('chr19:45387459-45387459', genome='hg19')

# Run Enformer
result = enformer_help.run_enformer(seq)

# Check predictions
print(f"Human tracks: {result['human'].shape}")
print(f"Mouse tracks: {result['mouse'].shape}")
```

### Example 3: Search and Plot
```python
import enformer_help

# Find DNase tracks
enformer_help.search_tracks('dnase')

# Run prediction
seq = enformer_help.getseq('chr1:1000000-1000100', genome='hg19')
result = enformer_help.run_enformer(seq)

# Plot track 45 (example)
enformer_help.trackplot(
    title="DNase predictions",
    track=result['human'][0, :, 45],
    snp_pos=1000050
)
```

## Performance

- **Sequence retrieval**: 1-10ms (local)
- **Enformer inference**: 5-10 seconds (CPU)
- **Cache lookup**: <1ms
- **Typical rate**: 0.05-0.1 SNPs/second (new)
- **Cached rate**: 1-10 SNPs/second

## Tips

1. ✅ Always use `import enformer_help` (underscore)
2. ✅ Use `--resume` to skip cached results
3. ✅ Use sorted file to process significant SNPs first
4. ✅ Add `--negative-control` for statistical comparison
5. ✅ Monitor cache size: `du -sh cache/`
6. ✅ Use `screen` or `tmux` for long-running jobs

## Support

For issues:
- Check `INSTALL.md` for installation problems
- Check `CACHE_EXPLAINED.md` for caching questions
- Check `PARALLEL_USAGE.md` for batch processing
- Run test scripts in package directory
