"""Tests for PDF to Visio Converter."""

import os
import sys
import tempfile
import shutil

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_to_visio import PDFConverter, convert_pdf, ConversionResult


def create_test_pdf(tmp_dir: str, content: str = "Test") -> str:
    """Create a minimal test PDF in the temp directory."""
    import pymupdf

    pdf_path = os.path.join(tmp_dir, "test.pdf")
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), content, fontsize=14)

    # Add a line for vector test
    shape = page.new_shape()
    shape.draw_line(pymupdf.Point(100, 200), pymupdf.Point(500, 200))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()

    doc.save(pdf_path)
    doc.close()

    return pdf_path


def test_converter_initialization():
    """Test converter can be initialized with valid PDF."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Init Test")

    try:
        converter = PDFConverter(pdf_path)
        assert converter.pdf_path == pdf_path
        assert converter.get_page_count() == 1
    finally:
        shutil.rmtree(tmp_dir)


def test_converter_invalid_file():
    """Test converter raises error for invalid file."""
    try:
        PDFConverter("nonexistent.pdf")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_to_svg_conversion():
    """Test PDF to SVG conversion."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "SVG Conversion Test")
    output_dir = tempfile.mkdtemp()

    try:
        converter = PDFConverter(pdf_path)
        result = converter.to_svg(output_dir)

        assert result.success is True, f"Conversion failed: {result.errors}"
        assert result.pages_converted == 1
        assert len(result.errors) == 0

        # Check output file exists
        output_files = os.listdir(output_dir)
        assert len(output_files) == 1
        assert output_files[0].endswith(".svg")

        # Check SVG content has vectors and text
        svg_path = os.path.join(output_dir, output_files[0])
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "<svg" in content

    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_extract_text():
    """Test text extraction from PDF."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Extract Text Test")

    try:
        converter = PDFConverter(pdf_path)
        text = converter.extract_text(0)
        assert "Extract Text Test" in text
    finally:
        shutil.rmtree(tmp_dir)


def test_extract_drawings():
    """Test vector drawing extraction."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Drawing Test")

    try:
        converter = PDFConverter(pdf_path)
        drawings = converter.extract_drawings(0)
        # Should have at least one drawing (the line)
        assert len(drawings) >= 1
    finally:
        shutil.rmtree(tmp_dir)


def test_convenience_function():
    """Test the convenience convert_pdf function."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Convenience Test")
    output_dir = tempfile.mkdtemp()

    try:
        result = convert_pdf(pdf_path, output_dir)
        assert result.success is True
        assert result.pages_converted == 1
    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_multiple_pages():
    """Test conversion of multi-page PDF."""
    tmp_dir = tempfile.mkdtemp()
    output_dir = tempfile.mkdtemp()

    # Create multi-page PDF
    pdf_path = os.path.join(tmp_dir, "multi.pdf")
    import pymupdf

    doc = pymupdf.open()

    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), f"Page {i + 1}", fontsize=14)

    doc.save(pdf_path)
    doc.close()

    try:
        converter = PDFConverter(pdf_path)
        result = converter.to_svg(output_dir)

        assert result.success is True
        assert result.pages_converted == 3

        output_files = sorted(os.listdir(output_dir))
        assert len(output_files) == 3
    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


if __name__ == "__main__":
    print("Running PDF to Visio Converter tests...")

    test_converter_initialization()
    print("[PASS] test_converter_initialization")

    test_converter_invalid_file()
    print("[PASS] test_converter_invalid_file")

    test_to_svg_conversion()
    print("[PASS] test_to_svg_conversion")

    test_extract_text()
    print("[PASS] test_extract_text")

    test_extract_drawings()
    print("[PASS] test_extract_drawings")

    test_convenience_function()
    print("[PASS] test_convenience_function")

    test_multiple_pages()
    print("[PASS] test_multiple_pages")

    print("\n*** ALL TESTS PASSED ***")
