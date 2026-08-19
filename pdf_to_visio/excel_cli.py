"""Command-line interface for Excel wire-list to Visio drawing conversion."""

import argparse
import sys

from .excel_converter import convert_excel_to_visio


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="excel2visio",
        description="Convert an Excel wire list to a Visio-importable SVG or native VSDX.",
    )
    parser.add_argument("excel", help="Input .xlsx wire-list path")
    parser.add_argument("output", help="Output .svg or .vsdx path")
    parser.add_argument(
        "--sheet",
        default=None,
        help="Worksheet name. Omit to use the active sheet.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Drawing title. Defaults to the Excel file stem.",
    )

    args = parser.parse_args()

    try:
        print(
            convert_excel_to_visio(
                args.excel,
                args.output,
                sheet=args.sheet,
                title=args.title,
            )
        )
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
