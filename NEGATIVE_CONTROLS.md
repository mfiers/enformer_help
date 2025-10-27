# Negative Control Feature

## Overview

The batch_enformer.py script now supports automatic generation of **negative control positions** for each SNP processed. This is useful for comparing the functional impact of variants at causal positions versus neutral positions.

## What Are Negative Controls?

For each SNP at position X with alleles A→G, the script can:

1. **Process the actual SNP** at chromosome:position (effect vs non-effect alleles)
2. **Process a control** at chromosome:(position + offset) with the same alleles inserted

The control position is typically chosen to be in a neutral region (e.g., 5kb upstream) where the variant is not expected to have functional effects.

## Usage

### Basic Command with Controls

```bash
# Add 5kb upstream controls
python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 1000 --negative-control 5000
```

### Parameters

- `--negative-control N`: Offset in base pairs for control position
  - Positive values: downstream (e.g., 5000 = +5kb)
  - Negative values: upstream (e.g., -5000 = -5kb)
  - Omit to disable controls

### Example Usage

```bash
# Process 100 SNPs with 5kb downstream controls
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 100 \
    --negative-control 5000

# Process with 10kb upstream controls
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 100 \
    --negative-control -10000

# With resume mode
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    --negative-control 5000 \
    --resume
```

## How It Works

### For Each SNP

**Example**: SNP at chr1:1000000, A→G

1. **Main SNP Processing**:
   - Retrieves sequence centered at chr1:1000000
   - Creates two sequences:
     - Effect sequence: reference with A at position
     - Non-effect sequence: reference with G at position
   - Runs Enformer on both sequences

2. **Control Processing** (with `--negative-control 5000`):
   - Retrieves sequence centered at chr1:1005000 (+5kb)
   - Gets reference allele at control position (e.g., C)
   - Creates two control sequences:
     - Control effect: reference with A inserted at chr1:1005000
     - Control non-effect: reference with G inserted at chr1:1005000
   - Runs Enformer on both control sequences

### Caching

Controls are cached independently:
- Each control sequence gets its own SHA256 hash
- Controls from previous runs are automatically reused
- `--resume` mode skips both SNPs and controls that are cached

## Output

### VCF File

When controls are enabled, a VCF file is automatically created:

```
controls_<input_filename>.vcf
```

**Example**: `controls_Kunkle_etal_Stage1_results.vcf`

### VCF Format

```vcf
##fileformat=VCFv4.2
##source=enformer_batch_processor
##INFO=<ID=TYPE,Number=1,Type=String,Description="SNP or CONTROL">
##INFO=<ID=ORIGINAL_SNP,Number=1,Type=String,Description="Original SNP ID for controls">
##INFO=<ID=REF_ALLELE,Number=1,Type=String,Description="Reference allele at this position">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	100000012	rs10875231	G	T	.	.	TYPE=SNP
1	100005012	rs10875231_control	C	T,G	.	.	TYPE=CONTROL;ORIGINAL_SNP=rs10875231;REF_ALLELE=C
```

### VCF Fields

- **CHROM**: Chromosome
- **POS**: Position (SNP or control)
- **ID**:
  - Main SNP: Original SNP ID
  - Control: `<original_id>_control`
- **REF**: Reference allele at this position
- **ALT**: Alternate allele(s) tested
- **INFO**:
  - `TYPE`: SNP or CONTROL
  - `ORIGINAL_SNP`: Links control back to source SNP
  - `REF_ALLELE`: Actual reference allele at position

## Progress Tracking

With controls enabled, the progress bar shows:

```
Processing:  45%|████████     | 45/100 [05:23<06:45, 1.35SNP/s] snp_new=12 snp_cache=30 ctrl_new=10 failed=3
```

Where:
- **snp_new**: New SNP predictions computed
- **snp_cache**: SNPs loaded from cache
- **ctrl_new**: New control predictions computed
- **failed**: Total failures (SNPs + controls)

## Statistics

Final output includes separate statistics for SNPs and controls:

```
======================================================================
FINAL STATISTICS
======================================================================
Total SNPs:                     100

Main SNPs:
  Newly computed:               25 (ran model)
  Loaded from cache:            70 (already computed)
  Failed:                       5

Negative Controls:
  Newly computed:               22
  Loaded from cache:            65
  Failed:                       13

Control VCF output:             controls_Kunkle_etal_Stage1_results.vcf

Total time:                     1250.5 seconds (20.8 minutes)
Overall SNP rate:               0.08 SNPs/second
Total controls processed:       87
======================================================================
```

## Use Cases

### 1. Variant Prioritization

Compare Enformer predictions between actual SNPs and control positions:

```python
import pandas as pd

# Load your analysis results
# For each SNP, compare prediction differences at:
# - Actual position (functional signal)
# - Control position (background/neutral)

# SNPs with larger effects at actual vs control positions
# are more likely to be functionally relevant
```

### 2. Statistical Power Estimation

Use controls to establish a null distribution of prediction differences:

```python
# Distribution of differences at control positions
# represents background variation
# Can be used to compute empirical p-values
```

### 3. False Discovery Rate Control

Controls help estimate the false positive rate:

```python
# Significant hits in controls = false positives
# FDR = (hits in controls) / (hits in SNPs)
```

## Performance Impact

### Additional Compute Time

With controls enabled:
- **Sequence retrieval**: ~2x time (retrieving 2 positions per SNP)
- **Enformer computation**: ~2x time (running on 4 sequences instead of 2)
- **Overall**: Approximately **2x total runtime**

### Cache Benefits

Controls are cached independently:
- First run: 2x time
- Subsequent runs with `--resume`: Only new controls computed
- Mixed datasets: Controls reused across different SNP sets if positions overlap

## Example Workflow

```bash
# Step 1: Process initial SNPs with controls
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 10000 \
    --negative-control 5000

# Step 2: Resume with more SNPs (cached results reused)
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 20000 \
    --negative-control 5000 \
    --resume

# Step 3: Analyze VCF and cached Enformer results
python analyze_controls.py controls_Kunkle_etal_Stage1_results.vcf
```

## Control Position Selection

### Recommended Offsets

- **5kb (5000 bp)**: Common choice, likely outside most regulatory elements
- **10kb (10000 bp)**: More conservative, further from potential cis-regulatory regions
- **50kb (50000 bp)**: Very conservative, reduces false positives from long-range elements

### Considerations

1. **Too close** (<1kb): May still be in functional regions
2. **Too far** (>100kb): Different regulatory context, not comparable
3. **Chromosome boundaries**: Script handles edge cases gracefully

### Direction (upstream vs downstream)

Use positive values for **downstream** (typical):
```bash
--negative-control 5000  # +5kb downstream
```

Use negative values for **upstream**:
```bash
--negative-control -5000  # 5kb upstream
```

## Troubleshooting

### Control Failures

Controls may fail more often than SNPs due to:
- **Chromosome edges**: Control position outside chromosome bounds
- **Assembly gaps**: Control position in unsequenced region
- **Reference issues**: UCSC cannot retrieve sequence

**Solution**: This is expected and handled gracefully. Failed controls are logged but don't stop processing.

### VCF Not Created

**Problem**: VCF file not generated

**Solution**:
- Ensure `--negative-control` is specified
- Check write permissions in current directory
- Verify at least one SNP was successfully processed

### High Control Failure Rate

**Problem**: >50% of controls failing

**Possible causes**:
- Offset too large (near chromosome boundaries)
- Assembly issues
- Chromosome naming mismatch

**Solution**: Try smaller offset or different direction

## Advanced Usage

### Multiple Control Positions

To process multiple control offsets, run the script multiple times:

```bash
# 5kb controls
python batch_enformer.py file.txt --negative-control 5000

# 10kb controls
python batch_enformer.py file.txt --negative-control 10000 --resume

# 50kb controls
python batch_enformer.py file.txt --negative-control 50000 --resume
```

Each run creates a separate VCF file.

### Combining with Other Options

```bash
# Full featured run
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 50000 \                    # Process 50k SNPs
    -s 10000 \                    # Skip first 10k
    --negative-control 5000 \     # 5kb controls
    --filter-indels \             # Only SNPs (no indels)
    --resume \                    # Use cache
    -w 10                         # 10 workers
```

## Limitations

1. **Single offset per run**: Only one control position per execution
2. **Same alleles**: Controls use the same alleles as the SNP (A→G in both)
3. **No matched controls**: Control positions are not matched for sequence context
4. **Linear offset**: Simple fixed offset, not considering genomic features

## Future Enhancements

Potential improvements:
- Multiple control positions per SNP
- Matched controls (similar GC content, conservation, etc.)
- Region-aware controls (avoid known functional regions)
- Randomized control positions

## Questions?

For issues or questions about negative controls, please open an issue on the repository.
