"""
Command-line interface for pdf-to-visio-converter.

Usage:
    python -m pdf_to_visio drawing.pdf output/
    python -m pdf_to_visio drawing.pdf output/ --fmt dxf
    python -m pdf_to_visio drawing.pdf output/ --fmt emf --page 0
"""

import argparse
import sys
from . import convert_to_format


def main():
    parser = argparse.ArgumentParser(
        prog="pdf2cad",
        description="Convert PDF engineering drawings to SVG, DXF, EMF, or DWG.",
    )
    parser.add_argument("pdf", help="Input PDF file path")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument(
        "--fmt",
        default="svg",
        choices=["svg", "dxf", "emf", "dwg"],
        help="Output format (default: svg)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=None,
        help="Convert only this page (0-based). Omit for all pages.",
    )
    parser.add_argument(
        "--dxf-version",
        default="R2010",
        help="DXF version (default: R2010). E.g. R2018",
    )
    parser.add_argument(
        "--dwg-version",
        default="ACAD2018",
        help="DWG version (default: ACAD2018). E.g. ACAD2010",
    )

    args = parser.parse_args()

    try:
        paths = convert_to_format(
            args.pdf,
            args.output_dir,
            fmt=args.fmt,
            page=args.page,
            dxf_version=args.dxf_version,
            dwg_version=args.dwg_version,
        )
        for p in paths:
            print(p)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
