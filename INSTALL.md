# Installation Guide

## Quick Install

```bash
# Navigate to package directory
cd /data/teachers/software/enformer_help

# Install in editable mode
pip install -e .
```

## Important: Import Name

⚠️ **The import name is different from the package name!**

```python
# ✅ CORRECT - import with underscore
import enformer_help

# ❌ WRONG - don't use package name
import enformerhelp  # This will fail!
```

### Why the Different Names?

- **Package name** (for pip): `enformerhelp` (no underscore)
- **Module name** (for import): `enformer_help` (with underscore)
- **Directory name**: `enformer_help/` (with underscore)

Python imports match the directory name, not the package name.

## Verification

Test your installation:

```bash
python -c "import enformer_help; print('✓ Import successful!')"
```

Expected output:
```
✓ Import successful!
```

## Dependencies

Required packages (automatically installed with `pip install -e .`):

- pandas >= 1.3.0
- matplotlib >= 3.3.0
- seaborn >= 0.11.0
- pysam >= 0.15.0
- enformer-pytorch >= 0.1.0
- torch >= 1.9.0

## Local Package Notice

📍 **This package is NOT on PyPI**

This is a local package maintained at:
```
/data/teachers/software/enformer_help
```

To use it:
1. Install locally with `pip install -e .`
2. Or add to your `sys.path`:
   ```python
   import sys
   sys.path.insert(0, '/data/teachers/software/enformer_help')
   import enformer_help
   ```

## External Requirements

### Genome Files

Required for sequence retrieval:
- **hg19**: `/data/db/genomes/hg19/fasta/hg19.fa`
- **hg19 index**: `/data/db/genomes/hg19/fasta/hg19.fa.fai`

See `LOCAL_GENOME_SETUP.md` for adding other genomes.

### Track Files

Required for track search functionality:
- `cache/targets_mouse.pkl`
- `cache/targets_human.pkl`

### Enformer Model

Required for predictions:
- `/data/teachers/software/enformer_help/cache/hub/enformer`

## Troubleshooting

### "ModuleNotFoundError: No module named 'enformer_help'"

**Problem**: Package not installed or not in Python path

**Solutions**:

1. Install the package:
   ```bash
   cd /data/teachers/software/enformer_help
   pip install -e .
   ```

2. Or add to path in your script:
   ```python
   import sys
   sys.path.insert(0, '/data/teachers/software/enformer_help')
   import enformer_help
   ```

### "ModuleNotFoundError: No module named 'enformerhelp'"

**Problem**: Using wrong import name

**Solution**: Use underscore!
```python
import enformer_help  # Not enformerhelp
```

### "ModuleNotFoundError: No module named 'pysam'"

**Problem**: Missing dependency

**Solution**:
```bash
pip install pysam>=0.15.0
```

### "FileNotFoundError: Genome file not found"

**Problem**: Missing genome file

**Solution**: Check genome file location in `enformer_help/__init__.py`:
```python
GENOME_PATHS = {
    'hg19': '/data/db/genomes/hg19/fasta/hg19.fa',
    # ...
}
```

Verify file exists:
```bash
ls -l /data/db/genomes/hg19/fasta/hg19.fa
```

## Updating

Since this is installed in editable mode, changes to the code are immediately available:

```bash
cd /data/teachers/software/enformer_help
git pull  # If using git
# Changes are automatically reflected in your Python environment
```

To update dependencies:
```bash
pip install -e . --upgrade
```

## Uninstalling

```bash
pip uninstall enformerhelp
```

Note: This only removes the package registration, not the source files.

## Development Installation

For development with additional tools:

```bash
cd /data/teachers/software/enformer_help

# Install with development dependencies
pip install -e .[dev]

# Or use hatch
pip install hatch
hatch shell
```

## Usage After Installation

```python
import enformer_help

# Get sequence
seq = enformer_help.getseq('chr1:1000000-1000100', genome='hg19')

# Run Enformer
result = enformer_help.run_enformer(seq)

# Search tracks
enformer_help.search_tracks('dnase')
```

## Getting Help

- **README**: `README.md` - Overview and quick start
- **Local Genomes**: `LOCAL_GENOME_SETUP.md` - Genome file setup
- **Parallel Processing**: `PARALLEL_USAGE.md` - Batch processing guide
- **Negative Controls**: `NEGATIVE_CONTROLS.md` - Control feature guide
- **Cache Info**: `CACHE_EXPLAINED.md` - Caching behavior

## Summary

✅ Install: `pip install -e .` in package directory
✅ Import: `import enformer_help` (with underscore!)
✅ Local package: Not on PyPI
✅ Dependencies: Auto-installed with editable install
✅ Genomes: Local FASTA files required
