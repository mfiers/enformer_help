# EnformerHelp

A Python library providing helper functions to run and cache [Enformer](https://www.nature.com/articles/s41592-021-01252-x) genomic predictions with integrated UCSC genome browser support.

## Features

- **Smart Sequence Retrieval**: Automatically fetch DNA sequences from UCSC genome browser with automatic window sizing to Enformer's 196,608 bp requirement
- **Intelligent Caching**: SHA256-based caching for both DNA sequences and Enformer predictions to avoid redundant computations
- **Track Search**: Search and explore genomic tracks across mouse and human genomes
- **Visualization**: Built-in plotting utilities for genomic predictions with SNP and gene annotations
- **Memory Efficient**: Lazy loading of the Enformer model with automatic cleanup

## Installation

### Using pip

```bash
pip install enformerhelp
```

### Development Installation

This project uses [Hatch](https://hatch.pypa.io/) for project management. To set up a development environment:

```bash
# Clone the repository
git clone https://github.com/yourusername/enformer_help.git
cd enformer_help

# Install hatch if you don't have it
pip install hatch

# Create and activate development environment
hatch shell

# Or run commands directly
hatch run test
```

## Requirements

- Python >= 3.8
- pandas >= 1.3.0
- matplotlib >= 3.3.0
- seaborn >= 0.11.0
- ucsc-api >= 0.1.0
- enformer-pytorch >= 0.1.0
- torch >= 1.9.0

### External Data Requirements

- Pre-computed track files: `cache/targets_mouse.pkl` and `cache/targets_human.pkl`
- Enformer model weights (configurable path, default: `/mnt/storage/data/huggingface/hub/enformer`)

## Quick Start

```python
from enformer_help import getseq, run_enformer, search_tracks, trackplot

# Search for available genomic tracks
search_tracks("h3k27ac")

# Retrieve a DNA sequence from UCSC
sequence = getseq(
    region='chr19:44,900,254-44,911,047',
    genome='hg19'
)

# Run Enformer prediction (with caching)
output = run_enformer(sequence)

# Visualize results
trackplot(
    title="H3K27ac predictions",
    track=output['human'][0, :, 123],  # Example track
    snp_pos=44905650
)
```

## API Reference

### `search_tracks(keyword)`

Search for genomic tracks by keyword in both mouse and human track databases.

**Parameters:**
- `keyword` (str): Search term to find in track descriptions

**Example:**
```python
search_tracks("dnase")
```

### `getseq(region, genome='hg19', length=196_608, silent=False)`

Retrieve DNA sequences from UCSC genome browser with automatic window adjustment.

**Parameters:**
- `region` (str): Genomic region in format 'chr:start-end'
- `genome` (str): Genome assembly (e.g., 'hg19', 'hg38', 'mm10')
- `length` (int): Target sequence length (default: 196,608 for Enformer)
- `silent` (bool): Suppress informational messages

**Returns:**
- `str`: DNA sequence in uppercase

**Example:**
```python
seq = getseq('chr1:1,000,000-1,010,000', genome='hg38')
```

### `run_enformer(sequence)`

Execute Enformer model predictions with automatic caching.

**Parameters:**
- `sequence` (str): DNA sequence string (should be 196,608 bp)

**Returns:**
- Enformer output tensor with predictions

**Example:**
```python
predictions = run_enformer(sequence)
```

### `trackplot(title, track, snp_pos)`

Visualize genomic track predictions with annotations.

**Parameters:**
- `title` (str): Plot title
- `track` (tensor): Track predictions from Enformer output
- `snp_pos` (int): SNP genomic position for marking

**Returns:**
- matplotlib Figure object

**Example:**
```python
fig = trackplot("CTCF binding", output['human'][0, :, 45], snp_pos=1234567)
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
