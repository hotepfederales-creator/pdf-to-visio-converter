"""
PDF to Visio Converter - Local Python Implementation

Converts PDF engineering drawings to Visio-compatible SVG format.
Uses PyMuPDF to extract vector graphics, text, and images.

Architecture:
    PDF Input → PyMuPDF (extract) → SVG Output → Visio Import

Usage:
    from pdf_to_visio import PDFConverter

    converter = PDFConverter("drawing.pdf")
    converter.to_svg("output_dir/")
"""

import pymupdf
import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class ConversionResult:
    """Result of a PDF to SVG conversion."""

    success: bool
    input_file: str
    output_file: str
    pages_converted: int
    errors: List[str]

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<ConversionResult {status}: {self.pages_converted} pages, {self.input_file} -> {self.output_file}>"


class PDFConverter:
    """
    Converts PDF engineering drawings to SVG format.

    Uses PyMuPDF to extract:
    - Vector graphics (lines, curves, shapes)
    - Text with positioning
    - Images

    Output SVG can be imported directly into Visio.
    """

    def __init__(self, pdf_path: str):
        """
        Initialize converter with PDF file.

        Args:
            pdf_path: Path to input PDF file
        """
        self.pdf_path = pdf_path
        self._validate_input()

    def _validate_input(self):
        """Validate input PDF exists and is readable."""
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        # Verify it's a valid PDF
        try:
            doc = pymupdf.open(self.pdf_path)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")
            doc.close()
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {e}")

    def to_svg(
        self, output_dir: str, pages: Optional[List[int]] = None
    ) -> ConversionResult:
        """
        Convert PDF to SVG files.

        Args:
            output_dir: Directory to save SVG files
            pages: Optional list of page numbers (0-indexed).
                   If None, converts all pages.

        Returns:
            ConversionResult with conversion status
        """
        errors = []
        pages_converted = 0

        # Open PDF
        try:
            doc = pymupdf.open(self.pdf_path)
        except Exception as e:
            return ConversionResult(
                success=False,
                input_file=self.pdf_path,
                output_file="",
                pages_converted=0,
                errors=[str(e)],
            )

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Determine pages to convert
        if pages is None:
            pages = list(range(doc.page_count))

        base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]

        # Convert each page
        for page_num in pages:
            if page_num >= doc.page_count:
                errors.append(f"Page {page_num} out of range")
                continue

            try:
                page = doc.load_page(page_num)

                # Get SVG representation (can be str or bytes)
                svg_data = page.get_svg_image()

                # Ensure we have bytes for writing
                if isinstance(svg_data, str):
                    svg_data = svg_data.encode("utf-8")

                # Determine output path
                output_path = os.path.join(
                    output_dir, f"{base_name}_page_{page_num + 1}.svg"
                )

                # Write SVG to file
                with open(output_path, "wb") as f:
                    f.write(svg_data)

                pages_converted += 1

            except Exception as e:
                errors.append(f"Page {page_num}: {str(e)}")

        doc.close()

        return ConversionResult(
            success=pages_converted > 0 and len(errors) == 0,
            input_file=self.pdf_path,
            output_file=output_dir,
            pages_converted=pages_converted,
            errors=errors,
        )

    def to_svg_single(self, output_path: str, page: int = 0) -> ConversionResult:
        """
        Convert a single PDF page to SVG.

        Args:
            output_path: Path for output SVG file
            page: Page number (0-indexed)

        Returns:
            ConversionResult with conversion status
        """
        result = self.to_svg(
            output_dir=os.path.dirname(output_path) or ".", pages=[page]
        )

        # Update output file in result
        if result.success:
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            result.output_file = os.path.join(
                os.path.dirname(output_path) or ".", f"{base_name}_page_{page + 1}.svg"
            )

        return result

    def get_page_count(self) -> int:
        """Get number of pages in PDF."""
        doc = pymupdf.open(self.pdf_path)
        count = doc.page_count
        doc.close()
        return count

    def extract_drawings(self, page: int = 0) -> List[Dict[str, Any]]:
        """
        Extract vector drawings from a specific page.

        Args:
            page: Page number (0-indexed)

        Returns:
            List of drawing path dictionaries
        """
        doc = pymupdf.open(self.pdf_path)

        if page >= doc.page_count:
            doc.close()
            raise ValueError(f"Page {page} out of range")

        page_obj = doc.load_page(page)
        drawings = page_obj.get_drawings()

        doc.close()
        return drawings

    def extract_text(self, page: int = 0) -> str:
        """
        Extract text from a specific page.

        Args:
            page: Page number (0-indexed)

        Returns:
            Plain text from the page
        """
        doc = pymupdf.open(self.pdf_path)

        if page >= doc.page_count:
            doc.close()
            raise ValueError(f"Page {page} out of range")

        page_obj = doc.load_page(page)
        text = page_obj.get_text()

        doc.close()
        return text


def convert_pdf(pdf_path: str, output_dir: str) -> ConversionResult:
    """
    Convenience function to convert PDF to SVG.

    Args:
        pdf_path: Path to input PDF
        output_dir: Directory for output SVG files

    Returns:
        ConversionResult
    """
    converter = PDFConverter(pdf_path)
    return converter.to_svg(output_dir)
