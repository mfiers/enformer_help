# EnformerHelp

A Python library providing helper functions to run and cache [Enformer](https://www.nature.com/articles/s41592-021-01252-x) genomic predictions with local genome file support.

## Features

- **Smart Sequence Retrieval**: Automatically fetch DNA sequences from local genome files with automatic window sizing to Enformer's 196,608 bp requirement
- **Intelligent Caching**: SHA256-based caching for both DNA sequences and Enformer predictions to avoid redundant computations
- **Track Search**: Search and explore genomic tracks across mouse and human genomes
- **Visualization**: Built-in plotting utilities for genomic predictions with SNP and gene annotations
- **Memory Efficient**: Lazy loading of both genome files and the Enformer model with automatic cleanup
- **Local Genome Support**: Uses local FASTA files via pysam (no API rate limits!)

## Installation

⚠️ **This package is not on PyPI - install locally only**

```bash
cd /data/teachers/software/enformer_help
pip install -e .
```

### ⚠️ Import Name is Different!

```python
# ✅ CORRECT
import enformer_help

# ❌ WRONG
import enformerhelp
```

**Why?** Package name is `enformerhelp` but module directory is `enformer_help/`

📖 **See [INSTALL.md](INSTALL.md) for detailed installation instructions**

## Requirements

- Python >= 3.8
- pandas >= 1.3.0
- matplotlib >= 3.3.0
- seaborn >= 0.11.0
- pysam >= 0.15.0
- enformer-pytorch >= 0.1.0
- torch >= 1.9.0

### External Data Requirements

- Pre-computed track files: `cache/targets_mouse.pkl` and `cache/targets_human.pkl`
- Enformer model weights (configurable path, default: `/data/teachers/software/enformer_help/cache/hub/enformer`)
- Local genome FASTA files (indexed):
  - hg19: `/data/db/genomes/hg19/fasta/hg19.fa`
  - hg38: `/data/db/genomes/hg38/fasta/hg38.fa` (add as needed)

## Quick Start for Beginners

### Step 1: Import the package

```python
# Remember: use underscore in the import name!
import enformer_help
```

### Step 2: Find what tracks are available

"Tracks" are different types of genomic measurements (like DNase, histone marks, transcription factors). Let's search for tracks related to a specific term:

```python
# Search for DNase hypersensitivity tracks
enformer_help.search_tracks("dnase")

# Or search for histone modifications
enformer_help.search_tracks("h3k27ac")
```

This will print a list of available tracks with their numbers (you'll need these numbers later!).

### Step 3: Get a DNA sequence

Tell Enformer which region of the genome you want to analyze:

```python
# Get sequence from chromosome 19, position 44,900,254 to 44,911,047
# The function automatically adjusts to exactly 196,608 bases (what Enformer needs)
sequence = enformer_help.getseq(
    region='chr19:44,900,254-44,911,047',  # Genomic coordinates
    genome='hg19'                           # Genome version (hg19 or hg38)
)

# Check what we got
print(f"Sequence length: {len(sequence)} bases")
print(f"First 50 bases: {sequence[:50]}")
```

### Step 4: Run Enformer predictions

This is the main step - running the deep learning model to predict genomic activity:

```python
# Run Enformer (this takes 5-10 seconds the first time)
# Results are automatically cached for reuse!
output = enformer_help.run_enformer(sequence)

# Check what we got back
print(f"Human predictions shape: {output['human'].shape}")
print(f"Mouse predictions shape: {output['mouse'].shape}")

# The output contains predictions for:
# - 896 bins (genomic windows)
# - Hundreds of tracks (different measurements)
```

### Step 5: Visualize the results

Now let's plot the predictions for a specific track:

```python
# Simple plot: just show predictions for track 123
fig = enformer_help.trackplot(
    title="H3K27ac predictions",      # Your plot title
    track=output['human'][0, :, 123],  # Track #123 for humans
    snp_pos=44905650                    # Mark your SNP position
)

# To show the plot (in Jupyter) or save it:
import matplotlib.pyplot as plt
plt.show()                              # Show in notebook
# OR
fig.savefig('my_plot.png')             # Save to file
```

### Complete Example: Analyzing a SNP

Here's a complete workflow from start to finish:

```python
import enformer_help
import matplotlib.pyplot as plt

# 1. Get the DNA sequence around your SNP
my_snp_position = 45387459  # Example: top Alzheimer's SNP
sequence = enformer_help.getseq(
    region=f'chr19:{my_snp_position}-{my_snp_position}',
    genome='hg19'
)

# 2. Run Enformer
print("Running Enformer... (this takes ~10 seconds)")
predictions = enformer_help.run_enformer(sequence)

# 3. Search for interesting tracks
print("\nSearching for DNase tracks...")
enformer_help.search_tracks("dnase")

# 4. Plot DNase track with gene markers
apoe_region_marks = [
    (45411941, 'red', 'APOE'),      # Mark APOE gene
    (45395619, 'blue', 'TOMM40')    # Mark nearby gene
]

fig = enformer_help.trackplot(
    title="DNase predictions near APOE",
    track=predictions['human'][0, :, 88],  # Track 88 is a DNase track
    snp_pos=my_snp_position,
    marks=apoe_region_marks
)

# 5. Save your plot
fig.savefig('apoe_snp_predictions.png', dpi=300, bbox_inches='tight')
print("\n✓ Plot saved as 'apoe_snp_predictions.png'")
```

## API Reference

### `search_tracks(keyword)`

**What it does:** Searches for genomic tracks (like DNase, histone marks, etc.) that match your keyword.

**Parameters:**
- `keyword` (str): The term you want to search for
  - Examples: "dnase", "h3k27ac", "ctcf", "pol2"
  - Not case-sensitive ("DNase" and "dnase" work the same)

**What it prints:**
- A table showing matching tracks with:
  - Track number (you'll need this for plotting!)
  - Description of what the track measures

**Example:**
```python
# Find all DNase hypersensitivity tracks
enformer_help.search_tracks("dnase")

# Find histone modification tracks
enformer_help.search_tracks("h3k4me3")
```

**Tip for beginners:** Run this first to find the track number you want to plot!

---

### `getseq(region, genome='hg19', length=196_608, silent=False)`

**What it does:** Gets a DNA sequence from your local genome file for a specific region.

**Parameters:**
- `region` (str): Where in the genome you want the sequence from
  - Format: `'chr:start-end'` or just `'chr:position-position'`
  - Examples: `'chr1:1000000-1000100'` or `'chr19:45387459-45387459'`
  - Can use commas: `'chr1:1,000,000-1,010,000'` (commas are ignored)
- `genome` (str, optional): Which genome version to use
  - Options: `'hg19'` (default), `'hg38'`
  - Default: `'hg19'`
- `length` (int, optional): How long the sequence should be
  - Default: 196,608 (what Enformer needs)
  - The function automatically centers your region and adjusts to this length
- `silent` (bool, optional): Set to `True` to hide progress messages
  - Default: `False` (shows what it's doing)

**Returns:**
- A string containing the DNA sequence in uppercase letters (A, C, G, T)

**Examples:**
```python
# Get sequence around a specific position
seq = enformer_help.getseq('chr1:1000000-1000100', genome='hg19')

# Get sequence for a single SNP position (auto-expands to 196,608 bp)
seq = enformer_help.getseq('chr19:45387459-45387459', genome='hg19')

# Quiet mode (no messages printed)
seq = enformer_help.getseq('chr1:1000000-1000100', silent=True)
```

**What happens behind the scenes:**
1. Your coordinates are centered
2. The region is expanded to exactly 196,608 bases
3. The sequence is retrieved from the local genome file
4. The sequence is cached (saved) so next time is instant!

---

### `run_enformer(sequence)`

**What it does:** Runs the Enformer deep learning model to predict genomic activity for your sequence.

**Parameters:**
- `sequence` (str): Your DNA sequence
  - Should be exactly 196,608 bases long (use `getseq()` to get the right length!)
  - Should only contain: A, C, G, T, or N

**Returns:**
- A dictionary with two keys:
  - `'human'`: Predictions for human cell types
  - `'mouse'`: Predictions for mouse cell types
- Each contains a PyTorch tensor with shape: (1, 896, num_tracks)
  - 1: Batch size (always 1)
  - 896: Number of genomic bins (windows)
  - num_tracks: Number of different measurements (varies)

**Examples:**
```python
# Basic usage
predictions = enformer_help.run_enformer(sequence)

# Access human predictions
human_preds = predictions['human']
print(human_preds.shape)  # Shows (1, 896, 5313) or similar

# Access predictions for a specific track
track_123 = predictions['human'][0, :, 123]  # Get track 123
```

**Important notes:**
- **First run takes ~10 seconds** (loading the model)
- **Subsequent runs are cached** and instant if you use the same sequence!
- **Each sequence result is ~50-100 MB** (stored in `cache/enformer/`)
- **Works on CPU** (no GPU needed, but slower than with GPU)

**Understanding the output:**
```python
predictions = enformer_help.run_enformer(sequence)

# predictions['human'] has shape (1, 896, 5313)
#   1 = batch dimension (always 1)
#   896 = genomic bins (each is 128 bp)
#   5313 = number of tracks (DNase, histones, etc.)

# To get a specific track for plotting:
track_data = predictions['human'][0, :, 88]  # Track 88
#   [0, :, 88] means:
#   0 = first (only) item in batch
#   : = all 896 bins
#   88 = track number 88
```

### `trackplot(title, track, snp_pos=None, marks=None)`

Visualize genomic track predictions with annotations.

**What it does:** Creates a scatter plot showing Enformer predictions across a genomic region, with optional markers for SNPs and genes.

**Parameters:**
- `title` (str): Title for your plot (e.g., "DNase predictions")
- `track` (tensor): The prediction values from Enformer output
  - This is a PyTorch tensor with predictions for each 128bp bin
  - Example: `output['human'][0, :, 123]` means track #123 for humans
- `snp_pos` (int, optional): Genomic position of your SNP
  - If provided, draws a gray vertical line at this position
  - Default: None (no SNP marker)
- `marks` (list, optional): Additional positions to mark on the plot
  - Format: List of tuples `[(position, color, label), ...]`
  - Example: `[(45411941, 'red', 'APOE'), (45395619, 'blue', 'TOMM40')]`
  - Each tuple is: (genomic_position, line_color, text_label)
  - Default: None (no additional markers)

**Returns:**
- A matplotlib Figure object that you can save or display

**Examples:**

Simple plot with just SNP position:
```python
fig = enformer_help.trackplot(
    title="CTCF binding predictions",
    track=output['human'][0, :, 45],
    snp_pos=1234567
)
```

Plot with multiple gene markers:
```python
# Mark APOE gene and other nearby genes
marks = [
    (45411941, 'red', 'APOE'),      # APOE gene in red
    (45395619, 'blue', 'TOMM40'),   # TOMM40 gene in blue
    (45424351, 'green', 'NECTIN2')  # NECTIN2 gene in green
]

fig = enformer_help.trackplot(
    title="DNase hypersensitivity near APOE",
    track=output['human'][0, :, 88],
    snp_pos=45387459,  # Your SNP position
    marks=marks         # Additional gene markers
)

# Save the figure
fig.savefig('my_plot.png', dpi=300, bbox_inches='tight')
```

## Caching

EnformerHelp implements two levels of caching:

1. **DNA Sequence Cache** (`cache/dna/`): Stores retrieved sequences from UCSC to avoid redundant API calls
2. **Enformer Output Cache** (`cache/enformer/`): Stores model predictions using SHA256 hash of input sequences

Caches are automatically created and managed. The library respects file system permissions and will skip caching if write access is unavailable.

## Development

### Running Tests

```bash
hatch run test
```

### Code Quality

```bash
# Format code
hatch run lint:fmt

# Run linters
hatch run lint:style

# Type checking
hatch run lint:typing

# Run all checks
hatch run lint:all
```

### Building Package

```bash
hatch build
```

## Citation

If you use this library in your research, please cite the original Enformer paper:

```bibtex
@article{avsec2021effective,
  title={Effective gene expression prediction from sequence by integrating long-range interactions},
  author={Avsec, {\v{Z}}iga and Agarwal, Vikram and Visentin, Daniel and Ledsam, Joseph R and Grabska-Barwinska, Agnieszka and Taylor, Kyle R and Assael, Yannis and Jumper, John and Kohli, Pushmeet and Kelley, David R},
  journal={Nature Methods},
  volume={18},
  number={10},
  pages={1196--1203},
  year={2021},
  publisher={Nature Publishing Group}
}
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
