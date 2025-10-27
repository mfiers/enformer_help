#!/usr/bin/env python
"""
Sort Kunkle SNP file by p-value (most significant first).
"""

import argparse
import pandas as pd
import sys
from pathlib import Path


def sort_kunkle_file(input_file, output_file=None, top_n=None):
    """
    Sort Kunkle SNP file by p-value.

    Args:
        input_file: Path to input Kunkle file
        output_file: Path to output file (default: input_file with _sorted_pvalue suffix)
        top_n: Only keep top N most significant SNPs (optional)
    """

    print("="*70)
    print("Sorting Kunkle SNP File by P-value")
    print("="*70)
    print()

    input_path = Path(input_file)

    if output_file is None:
        # Create output filename
        output_file = input_path.parent / f"{input_path.stem}_sorted_pvalue{input_path.suffix}"

    print(f"Input file:  {input_file}")
    print(f"Output file: {output_file}")
    if top_n:
        print(f"Keeping top: {top_n:,} SNPs")
    print()

    # Read the file
    print("Reading file...")
    try:
        # Define column names
        columns = ['Chromosome', 'Position', 'MarkerName', 'Effect_allele',
                   'Non_Effect_allele', 'Beta', 'SE', 'Pvalue']

        # Read with specified dtypes for efficiency
        # Don't specify Position as int to handle NA values
        dtypes = {
            'Chromosome': str,
            'MarkerName': str,
            'Effect_allele': str,
            'Non_Effect_allele': str,
            'Beta': float,
            'SE': float,
            'Pvalue': float
        }

        df = pd.read_csv(
            input_file,
            sep=r'\s+',  # Whitespace separator
            names=columns,
            dtype=dtypes,
            skiprows=1,  # Skip header
            engine='python'  # Required for regex separator
        )

        # Convert Position to numeric, coercing errors to NaN
        df['Position'] = pd.to_numeric(df['Position'], errors='coerce')

        print(f"✓ Loaded {len(df):,} SNPs")
        print()

    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False

    # Show p-value range before sorting
    print("P-value statistics (before sorting):")
    print(f"  Min:    {df['Pvalue'].min():.2e}")
    print(f"  Max:    {df['Pvalue'].max():.2e}")
    print(f"  Median: {df['Pvalue'].median():.2e}")
    print(f"  Mean:   {df['Pvalue'].mean():.2e}")
    print()

    # Sort by p-value (ascending - lowest p-values first)
    print("Sorting by p-value (most significant first)...")
    df_sorted = df.sort_values('Pvalue', ascending=True)
    print("✓ Sorted")
    print()

    # Keep top N if requested
    if top_n is not None and top_n < len(df_sorted):
        print(f"Keeping top {top_n:,} most significant SNPs...")
        df_sorted = df_sorted.head(top_n)
        print("✓ Filtered")
        print()

    # Show top SNPs
    print("Top 10 most significant SNPs:")
    print(df_sorted[['Chromosome', 'Position', 'MarkerName', 'Pvalue']].head(10).to_string(index=False))
    print()

    # Write sorted file
    print(f"Writing to {output_file}...")
    try:
        # Write with header
        with open(output_file, 'w') as f:
            # Write header
            f.write(' '.join(columns) + '\n')

            # Write data
            df_sorted.to_csv(f, sep=' ', header=False, index=False)

        print(f"✓ Wrote {len(df_sorted):,} SNPs")
        print()

    except Exception as e:
        print(f"✗ Error writing file: {e}")
        return False

    # Verify output
    print("Verification:")
    print(f"  Input lines:  {len(df):,}")
    print(f"  Output lines: {len(df_sorted):,}")

    # Show file sizes
    input_size = input_path.stat().st_size / (1024**3)
    output_size = Path(output_file).stat().st_size / (1024**3)
    print(f"  Input size:   {input_size:.2f} GB")
    print(f"  Output size:  {output_size:.2f} GB")
    print()

    print("="*70)
    print("✓ Complete!")
    print("="*70)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sort Kunkle SNP file by p-value (most significant first)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to input Kunkle SNP file"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input_file_sorted_pvalue.txt)"
    )
    parser.add_argument(
        "-n", "--top",
        type=int,
        default=None,
        help="Only keep top N most significant SNPs"
    )

    args = parser.parse_args()

    # Run sorting
    success = sort_kunkle_file(args.input_file, args.output, args.top)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
