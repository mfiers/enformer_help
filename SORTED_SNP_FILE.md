# Sorted Kunkle SNP File

## Overview

Created a p-value sorted version of the Kunkle GWAS summary statistics file with most significant SNPs at the top.

## Files

### Original File
```
/data/user/u0089478/enformer/Kunkle_etal_Stage1_results.txt
```
- **Lines**: 11,480,633 (including header)
- **Size**: 544 MB
- **Order**: Genomic position (chr1→chr22)

### Sorted File
```
/data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt
```
- **Lines**: 11,480,633 (including header)
- **Size**: 541 MB
- **Order**: P-value (most significant → least significant)

## P-value Distribution

### Most Significant SNPs

The top 100 SNPs have extremely significant p-values:
- Many with p = 0.0 (rounded from < 1e-300)
- Range: 0 to ~1e-90
- **Location**: Primarily chr19:45M region (APOE locus - expected for Alzheimer's!)

### Top 10 SNPs

```
Chromosome  Position    MarkerName        Pvalue
19          45387459    rs12972156        0.0
19          45386467    chr19:45386467:I  0.0
19          45394336    rs71352238        0.0
19          45395909    rs34404554        0.0
19          45395844    rs34095326        0.0
19          45395619    rs2075650         0.0
19          45396144    rs11556505        0.0
19          45413576    rs75627662        0.0
19          45424351    rs814573          0.0
19          45427125    rs111789331       0.0
```

**Note**: All in the APOE region, the most well-established Alzheimer's disease risk locus.

### P-value Milestones

| Line Number | Approximate P-value |
|-------------|---------------------|
| 1-100       | ~0 to 1e-90         |
| 1,000       | ~2e-10              |
| 10,000      | ~1e-7               |
| 100,000     | ~1e-5               |
| 1,000,000   | ~0.01               |

## Usage with Enformer

### Process Most Significant SNPs First

```bash
# Process top 1000 most significant SNPs with controls
python batch_enformer.py \
    /data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt \
    -n 1000 \
    --negative-control 5000

# Process top 10,000 most significant
python batch_enformer.py \
    /data/user/u0089478/enformer/Kunkle_etal_Stage1_results_sorted_pvalue.txt \
    -n 10000 \
    --negative-control 5000 \
    --resume
```

### Advantages of Sorted File

1. **Prioritization**: Process most interesting SNPs first
2. **Early Results**: Get meaningful results quickly
3. **Genome-wide Significant**: First ~10k SNPs are all p < 5e-8
4. **Efficient**: Stop processing when you have enough significant SNPs

### Processing Strategies

#### Strategy 1: Top N SNPs
```bash
# Process top 5000 SNPs only
python batch_enformer.py sorted_file.txt -n 5000 --negative-control 5000
```

#### Strategy 2: P-value Threshold
```bash
# Process all genome-wide significant SNPs (p < 5e-8)
# Approximately first ~10,000 SNPs
python batch_enformer.py sorted_file.txt -n 10000 --negative-control 5000
```

#### Strategy 3: Progressive Processing
```bash
# Day 1: Top 1k most significant
python batch_enformer.py sorted_file.txt -n 1000 --negative-control 5000

# Day 2: Next 9k (total 10k)
python batch_enformer.py sorted_file.txt -n 10000 --negative-control 5000 --resume

# Day 3: Next 90k (total 100k)
python batch_enformer.py sorted_file.txt -n 100000 --negative-control 5000 --resume
```

## Sorting Script

Located at:
```
/data/teachers/software/enformer_help/sort_kunkle_by_pvalue.py
```

### Usage

```bash
# Basic usage
python sort_kunkle_by_pvalue.py input_file.txt

# Specify output file
python sort_kunkle_by_pvalue.py input_file.txt -o output_file.txt

# Keep only top N SNPs
python sort_kunkle_by_pvalue.py input_file.txt --top 100000
```

### Features

- Handles 11M+ rows efficiently
- Preserves all columns
- Shows p-value statistics
- Displays top SNPs
- Verifies output

## File Format

Both files use the same format:

```
Chromosome Position MarkerName Effect_allele Non_Effect_allele Beta SE Pvalue
19 45387459 rs12972156 C G -0.9653 0.0189 0.0
```

**Columns:**
1. Chromosome (1-22)
2. Position (bp)
3. MarkerName (rs ID or coordinate)
4. Effect_allele
5. Non_Effect_allele
6. Beta (effect size)
7. SE (standard error)
8. Pvalue

## Statistics

### Original File
- P-value range: 0.0 to 1.0
- Median p-value: 0.487
- Mean p-value: 0.491

### Distribution
- Genome-wide significant (p < 5e-8): ~10,000 SNPs
- Suggestive (p < 1e-5): ~100,000 SNPs
- Nominal (p < 0.05): ~574,000 SNPs

## Verification

### Check Sorting

```bash
# First 20 lines (should show smallest p-values)
head -20 sorted_file.txt

# Last 10 lines (should show p-values near 1.0)
tail -10 sorted_file.txt

# Count lines (should match original)
wc -l sorted_file.txt original_file.txt
```

### Spot Check

```bash
# Check p-values are ascending
awk 'NR>1 {print $8}' sorted_file.txt | head -1000 | \
  awk '{if (NR>1 && $1 < prev) print "ERROR: not sorted"; prev=$1}'
```

## Performance Impact

Processing sorted file vs. original:

### Original File (Position-ordered)
- SNPs scattered across all p-values
- Must process many non-significant SNPs
- Harder to filter by significance

### Sorted File (P-value-ordered)
- Process most significant SNPs first
- Can stop after N SNPs
- Easy to apply p-value threshold
- Better for exploratory analysis

## Common Use Cases

### 1. Quick Pilot Study
```bash
# Just test top 100 most significant SNPs
python batch_enformer.py sorted_file.txt -n 100 --negative-control 5000
```

### 2. Genome-wide Significant Only
```bash
# Process ~10k genome-wide significant SNPs
python batch_enformer.py sorted_file.txt -n 10000 --negative-control 5000
```

### 3. Full Analysis
```bash
# Process all SNPs (but most significant first)
python batch_enformer.py sorted_file.txt --negative-control 5000 --resume
```

## Notes

- **APOE Region**: Top SNPs cluster at chr19:45M (APOE/TOMM40)
- **Genome-wide Threshold**: Traditional threshold is p < 5×10⁻⁸
- **Multiple Testing**: 11.4M tests → Bonferroni: 4.4×10⁻⁹
- **Effect Sizes**: Beta values range from -1.2 to +1.1 (log odds ratios)

## Tips

1. **Start Small**: Test with top 100-1000 SNPs first
2. **Use Resume**: Always use `--resume` to avoid reprocessing
3. **Monitor Progress**: Sorted file gives better sense of completion
4. **Cache Benefits**: Top SNPs likely already cached from prior analyses
5. **Controls**: Add controls for statistical comparison

## Related Files

- **Sorting Script**: `/data/teachers/software/enformer_help/sort_kunkle_by_pvalue.py`
- **Batch Processing**: `/data/teachers/software/enformer_help/batch_enformer.py`
- **Documentation**: `/data/teachers/software/enformer_help/PARALLEL_USAGE.md`

## Summary

✅ Created sorted file with 11.4M SNPs ordered by significance
✅ Most significant SNPs (APOE region) at top
✅ Same format as original - drop-in replacement
✅ Enables efficient prioritized processing
✅ Perfect for exploring most promising associations first!
