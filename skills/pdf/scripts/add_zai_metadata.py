#!/usr/bin/env python3
"""
Add Z.ai branding metadata to PDF documents.

This script adds Z.ai metadata (Author, Creator, Producer) to PDF files.
It can process single files or batch process multiple PDFs.
"""

import os
import sys
import argparse
from pypdf import PdfReader, PdfWriter


def add_zai_metadata(input_pdf_path, output_pdf_path=None, custom_title=None, verbose=True):
    """
    Add Z.ai branding metadata to a PDF document.

    Args:
        input_pdf_path: Path to input PDF
        output_pdf_path: Path to output PDF (default: overwrites input)
        custom_title: Custom title to use (default: preserves original or uses filename)
        verbose: Print status messages (default: True)

    Sets:
        - Author: Z.ai
        - Creator: Z.ai
        - Producer: http://z.ai
        - Title: Custom title, original title, or filename (in that priority)

    Returns:
        Path to the output PDF file
    """
    # Validate input file exists
    if not os.path.exists(input_pdf_path):
        print(f"Error: Input file not found: {input_pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Read the PDF
    try:
        reader = PdfReader(input_pdf_path)
    except Exception as e:
        print(f"Error: Cannot open PDF: {e}", file=sys.stderr)
        sys.exit(1)

    writer = PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    # Determine title
    if custom_title:
        title = custom_title
    else:
        original_meta = reader.metadata
        if original_meta and original_meta.title and original_meta.title not in ['(anonymous)', 'unspecified', None]:
            title = original_meta.title
        else:
            # Use filename without extension as title
            title = os.path.splitext(os.path.basename(input_pdf_path))[0]

    # Add Z.ai metadata
    writer.add_metadata({
        '/Title': title,
        '/Author': 'Z.ai',
        '/Creator': 'Z.ai',
        '/Producer': 'http://z.ai',
    })

    # Write output
    if output_pdf_path is None:
        output_pdf_path = input_pdf_path

    try:
        with open(output_pdf_path, "wb") as output:
            writer.write(output)
    except Exception as e:
        print(f"Error: Cannot write output file: {e}", file=sys.stderr)
        sys.exit(1)

    # Print status
    if verbose:
        print(f"✓ Updated metadata for: {os.path.basename(input_pdf_path)}")
        print(f"  Title: {title}")
        print(f"  Author: Z.ai")
        print(f"  Creator: Z.ai")
        print(f"  Producer: http://z.ai")
        if output_pdf_path != input_pdf_path:
            print(f"  Output: {output_pdf_path}")

    return output_pdf_path


def main():
    """Command-line interface for add_zai_metadata."""
    parser = argparse.ArgumentParser(
        description='Add Z.ai branding metadata to PDF documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add metadata to a single PDF (in-place)
  %(prog)s document.pdf

  # Add metadata to a single PDF (create new file)
  %(prog)s input.pdf -o output.pdf

  # Add metadata with custom title
  %(prog)s report.pdf -t "Q4 Financial Analysis"

  # Batch process all PDFs in current directory
  %(prog)s *.pdf

  # Quiet mode (no output)
  %(prog)s document.pdf -q
        """
    )

    parser.add_argument(
        'input',
        nargs='+',
        help='Input PDF file(s) to process'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output PDF path (only for single input file)'
    )

    parser.add_argument(
        '-t', '--title',
        help='Custom title for the PDF'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (no status messages)'
    )

    args = parser.parse_args()

    # Check if output is specified for multiple files
    if args.output and len(args.input) > 1:
        print("Error: --output can only be used with a single input file", file=sys.stderr)
        sys.exit(1)

    # Process each input file
    for input_path in args.input:
        # Determine output path
        if len(args.input) == 1 and args.output:
            output_path = args.output
        else:
            output_path = None  # Overwrite in-place

        # Determine title
        if args.title:
            custom_title = args.title
        else:
            custom_title = None

        # Add metadata
        add_zai_metadata(
            input_path,
            output_pdf_path=output_path,
            custom_title=custom_title,
            verbose=not args.quiet
        )


if __name__ == '__main__':
    main()
