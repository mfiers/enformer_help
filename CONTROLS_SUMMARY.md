# Negative Controls Feature - Quick Reference

## ✨ What's New

The `batch_enformer.py` script now supports **automatic negative control generation** for each SNP processed.

## 🚀 Quick Start

```bash
# Add 5kb downstream controls to your SNP analysis
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 1000 \
    --negative-control 5000
```

## 🎯 What It Does

For each SNP (e.g., chr1:1000000 A→G):

1. **Main SNP**: Runs Enformer on sequences with A and G at position 1000000
2. **Control**: Runs Enformer on sequences with A and G inserted at position 1005000 (+5kb)

This allows you to compare functional predictions at the actual SNP location versus a neutral location.

## 📊 Output

### VCF File

Automatically creates: `controls_<input_filename>.vcf`

Example:
```vcf
#CHROM  POS        ID                    REF  ALT    INFO
1       100000012  rs10875231            G    T      TYPE=SNP
1       100005012  rs10875231_control    C    T,G    TYPE=CONTROL;ORIGINAL_SNP=rs10875231;REF_ALLELE=C
```

### Progress Bar

```
Processing:  45%|████| 45/100 [05:23<06:45] snp_new=12 snp_cache=30 ctrl_new=10 failed=3
```

- **snp_new**: New SNP predictions
- **snp_cache**: Cached SNP predictions
- **ctrl_new**: New control predictions
- **failed**: Total failures

### Statistics

```
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
```

## 💡 Usage Examples

### Basic Usage

```bash
# 5kb downstream controls
python batch_enformer.py file.txt -n 1000 --negative-control 5000

# 10kb upstream controls
python batch_enformer.py file.txt -n 1000 --negative-control -10000

# With resume mode (use cache)
python batch_enformer.py file.txt --negative-control 5000 --resume
```

### Recommended Offsets

- **5000** (5kb): Standard choice, likely outside most regulatory elements
- **10000** (10kb): More conservative
- **50000** (50kb): Very conservative for long-range effects

### Complete Example

```bash
# Process 10k SNPs with 5kb controls, using cache and 8 workers
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 10000 \
    --negative-control 5000 \
    --resume \
    -w 8
```

## ⚡ Performance

- **Runtime**: Approximately 2x (processing 4 sequences per SNP instead of 2)
- **Caching**: Controls are cached independently (reused across runs)
- **Resume mode**: Skips both cached SNPs and cached controls

## 📖 Analysis Workflow

1. **Run with controls**:
   ```bash
   python batch_enformer.py data.txt -n 1000 --negative-control 5000
   ```

2. **Load VCF to map SNPs to controls**:
   ```python
   import pandas as pd
   vcf = pd.read_csv('controls_data.vcf', sep='\t', comment='#')

   snps = vcf[vcf['INFO'].str.contains('TYPE=SNP')]
   controls = vcf[vcf['INFO'].str.contains('TYPE=CONTROL')]
   ```

3. **Load Enformer predictions from cache**:
   ```python
   import enformer_help

   # Get predictions for a sequence
   predictions = enformer_help.run_enformer(sequence)
   # This automatically uses cache if available
   ```

4. **Compare effect sizes**:
   ```python
   # For each SNP:
   #   - Calculate Euclidean distance between alleles at SNP position
   #   - Calculate Euclidean distance between alleles at control position
   #   - SNPs with larger effect at actual vs control = functional
   ```

## 🎓 Use Cases

### 1. Variant Prioritization
Compare prediction differences at SNP vs control positions to identify functionally relevant variants.

### 2. FDR Control
Estimate false discovery rate using control position results as null distribution.

### 3. Power Analysis
Use control distributions to estimate statistical power for detecting functional effects.

## ⚠️ Important Notes

- **Performance**: 2x runtime (processing controls takes as long as processing SNPs)
- **Disk space**: 2x cache size (controls cached separately)
- **Control failures**: Normal if controls near chromosome edges or in assembly gaps
- **Same alleles**: Controls use the same alleles as the SNP (not matched for context)

## 🔧 Troubleshooting

### VCF not created
- Make sure `--negative-control` is specified
- Check write permissions
- Verify at least one SNP succeeded

### High control failure rate (>50%)
- Try smaller offset (controls hitting chromosome boundaries)
- Check chromosome naming in input file
- Verify genome assembly (hg19 vs hg38)

## 📚 Full Documentation

See `NEGATIVE_CONTROLS.md` for complete documentation including:
- Detailed implementation
- VCF format specification
- Advanced usage examples
- Statistical analysis workflows

## 🧪 Testing

Test the feature with a small sample:

```bash
# Quick test with 5 SNPs
bash test_controls.sh

# Or manually:
python batch_enformer.py Kunkle_etal_Stage1_results.txt \
    -n 5 \
    --negative-control 5000
```

## 📝 Example VCF Record

```vcf
1  100005012  rs10875231_control  C  T,G  .  .  TYPE=CONTROL;ORIGINAL_SNP=rs10875231;REF_ALLELE=C
```

This means:
- **Control position**: chr1:100005012 (5kb from original SNP at chr1:100000012)
- **Original SNP**: rs10875231 (A→G at chr1:100000012)
- **Reference at control**: C
- **Tested alleles**: A and G (same as original SNP)
- **Purpose**: Compare Enformer predictions with A or G at this neutral position

## 🎉 Summary

The negative control feature allows you to:
1. ✅ Automatically generate control positions for each SNP
2. ✅ Run Enformer on both SNPs and controls
3. ✅ Get a VCF file mapping SNPs to their controls
4. ✅ Use controls for statistical comparison and FDR control
5. ✅ Leverage caching for efficient reprocessing

All with a single flag: `--negative-control 5000`
