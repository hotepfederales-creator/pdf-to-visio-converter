"""Tests for PDF to Visio Converter."""

import os
import sys
import tempfile
import shutil

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_to_visio import PDFConverter, convert_pdf, convert_to_format


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


def create_wire_list_xlsx(tmp_dir: str) -> str:
    """Create a minimal Excel harness wire list."""
    from openpyxl import Workbook

    excel_path = os.path.join(tmp_dir, "harness.xlsx")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Harness"
    sheet.append(
        [
            "From Connector",
            "From Pin",
            "To Connector",
            "To Pin",
            "Signal",
            "Wire Color",
            "AWG",
            "Breakout Jack",
        ]
    )
    sheet.append(["J1", "1", "J2", "A", "CAN_H", "Blue", "22", "TP1"])
    sheet.append(["J1", "2", "J2", "B", "CAN_L", "White", "22", "TP2"])
    workbook.save(excel_path)
    workbook.close()
    return excel_path


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


def test_svg_api_imports_without_ezdxf():
    """SVG-only users can import the package without optional ezdxf installed."""
    import subprocess

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (
        "import importlib.abc, sys\n"
        "class BlockEzdxf(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'ezdxf' or fullname.startswith('ezdxf.'):\n"
        "            raise ModuleNotFoundError(fullname)\n"
        "        return None\n"
        "sys.meta_path.insert(0, BlockEzdxf())\n"
        f"sys.path.insert(0, {repo_root!r})\n"
        "import pdf_to_visio\n"
        "assert pdf_to_visio.PDFConverter\n"
        "assert pdf_to_visio.convert_pdf\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


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


def test_negative_page_is_rejected():
    """Negative pages are invalid, not aliases for the last page."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Negative Page Test")
    output_dir = tempfile.mkdtemp()

    try:
        converter = PDFConverter(pdf_path)
        for operation in (converter.extract_text, converter.extract_drawings):
            try:
                operation(-1)
                assert False, "Should have rejected negative page"
            except ValueError as e:
                assert "Page -1" in str(e)

        try:
            convert_to_format(pdf_path, output_dir, fmt="svg", page=-1)
            assert False, "Should have rejected negative page"
        except ValueError as e:
            assert "Page -1" in str(e)
    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


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


def test_load_connections_from_excel():
    """Test Excel wire-list header aliases and row parsing."""
    tmp_dir = tempfile.mkdtemp()
    excel_path = create_wire_list_xlsx(tmp_dir)

    try:
        from pdf_to_visio import load_connections_from_excel

        connections = load_connections_from_excel(excel_path, sheet="Harness")

        assert len(connections) == 2
        assert connections[0].source.connector == "J1"
        assert connections[0].source.pin == "1"
        assert connections[0].destination.connector == "J2"
        assert connections[0].destination.pin == "A"
        assert connections[0].signal == "CAN_H"
        assert connections[0].breakout == "TP1"
    finally:
        shutil.rmtree(tmp_dir)


def test_convert_excel_to_visio_svg():
    """Test Excel wire list renders a Visio-importable SVG drawing."""
    tmp_dir = tempfile.mkdtemp()
    excel_path = create_wire_list_xlsx(tmp_dir)
    output_path = os.path.join(tmp_dir, "harness.svg")

    try:
        from pdf_to_visio import convert_excel_to_visio

        result = convert_excel_to_visio(excel_path, output_path, title="Bench Harness")

        assert result == os.path.abspath(output_path)
        with open(output_path, encoding="utf-8") as file:
            svg = file.read()
        assert "<svg" in svg
        assert "Bench Harness" in svg
        assert "J1 pin 1" in svg
        assert "J2 pin A" in svg
        assert "Breakout Box" in svg
        assert "TP1" in svg
    finally:
        shutil.rmtree(tmp_dir)


def test_excel_missing_required_columns():
    """Test Excel import reports missing required wire-list columns."""
    from openpyxl import Workbook

    tmp_dir = tempfile.mkdtemp()
    excel_path = os.path.join(tmp_dir, "bad.xlsx")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["From Connector", "From Pin"])
    sheet.append(["J1", "1"])
    workbook.save(excel_path)
    workbook.close()

    try:
        from pdf_to_visio import load_connections_from_excel

        try:
            load_connections_from_excel(excel_path)
            assert False, "Should have reported missing required columns"
        except ValueError as e:
            assert "Missing required Excel columns" in str(e)
            assert "destination_connector" in str(e)
    finally:
        shutil.rmtree(tmp_dir)


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


def test_dxf_conversion():
    """Test PDF to DXF conversion produces a valid DXF file."""
    import ezdxf

    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "DXF Test")
    output_dir = tempfile.mkdtemp()

    try:
        from pdf_to_visio import PDFtoDXFConverter

        converter = PDFtoDXFConverter(pdf_path)
        out_path = os.path.join(output_dir, "out.dxf")
        result = converter.convert(out_path, page=0)

        assert os.path.exists(result), "DXF file not created"
        assert result.endswith(".dxf")

        # Validate the DXF is parseable by ezdxf
        doc = ezdxf.readfile(result)
        msp = doc.modelspace()
        entities = list(msp)
        assert len(entities) > 0, "DXF modelspace has no entities"

    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_dxf_text_extraction():
    """Test that text spans are written to DXF as TEXT entities."""
    import ezdxf

    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "DXF Text Check")
    output_dir = tempfile.mkdtemp()

    try:
        from pdf_to_visio import PDFtoDXFConverter

        converter = PDFtoDXFConverter(pdf_path)
        out_path = os.path.join(output_dir, "out.dxf")
        converter.convert(out_path)

        doc = ezdxf.readfile(out_path)
        msp = doc.modelspace()
        texts = [e.dxf.text for e in msp if e.dxftype() == "TEXT"]
        # At least one TEXT entity should contain our label
        assert any("DXF Text Check" in t for t in texts), (
            f"Expected 'DXF Text Check' in TEXT entities, got: {texts}"
        )

    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_dxf_all_pages():
    """Test DXF conversion of all pages in a multi-page PDF."""
    import ezdxf

    tmp_dir = tempfile.mkdtemp()
    output_dir = tempfile.mkdtemp()

    pdf_path = os.path.join(tmp_dir, "multi.pdf")
    import pymupdf

    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), f"Page {i + 1}", fontsize=14)
    doc.save(pdf_path)
    doc.close()

    try:
        from pdf_to_visio import PDFtoDXFConverter

        converter = PDFtoDXFConverter(pdf_path)
        files = converter.convert_all_pages(output_dir)

        assert len(files) == 3
        for f in files:
            assert os.path.exists(f)
            ezdxf.readfile(f)  # must parse without error

    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_dxf_invalid_version():
    """Test that an unknown DXF version raises ValueError."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Version Test")

    try:
        from pdf_to_visio import PDFtoDXFConverter

        converter = PDFtoDXFConverter(pdf_path)
        try:
            converter.convert(os.path.join(tmp_dir, "out.dxf"), dxf_version="R9999")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    finally:
        shutil.rmtree(tmp_dir)


def test_convert_to_format_dxf():
    """Test the unified convert_to_format() for DXF output."""
    import ezdxf

    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Unified DXF")
    output_dir = tempfile.mkdtemp()

    try:
        from pdf_to_visio import convert_to_format

        paths = convert_to_format(pdf_path, output_dir, fmt="dxf")
        assert len(paths) == 1
        assert paths[0].endswith(".dxf")
        assert os.path.exists(paths[0])
        ezdxf.readfile(paths[0])

    finally:
        shutil.rmtree(tmp_dir)
        shutil.rmtree(output_dir)


def test_convert_to_format_unknown():
    """Test that an unknown format raises ValueError."""
    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "Unknown Format")

    try:
        from pdf_to_visio import convert_to_format

        try:
            convert_to_format(pdf_path, tmp_dir, fmt="pdf2jpg")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    finally:
        shutil.rmtree(tmp_dir)


def test_emf_requires_inkscape():
    """Test PDFtoEMFConverter raises RuntimeError when Inkscape is absent."""
    import unittest.mock as mock

    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "EMF Test")

    try:
        from pdf_to_visio import emf_converter

        # Patch _find_inkscape to simulate absence
        with mock.patch.object(emf_converter, "_find_inkscape", return_value=None):
            try:
                from pdf_to_visio import PDFtoEMFConverter

                PDFtoEMFConverter(pdf_path)
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "Inkscape" in str(e)

    finally:
        shutil.rmtree(tmp_dir)


def test_dwg_requires_oda():
    """Test PDFtoDWGConverter raises RuntimeError when ODA is absent."""
    import unittest.mock as mock

    tmp_dir = tempfile.mkdtemp()
    pdf_path = create_test_pdf(tmp_dir, "DWG Test")

    try:
        from pdf_to_visio import dwg_converter

        with mock.patch.object(dwg_converter, "_find_oda", return_value=None):
            try:
                from pdf_to_visio import PDFtoDWGConverter

                PDFtoDWGConverter(pdf_path)
                assert False, "Should have raised RuntimeError"
            except RuntimeError as e:
                assert "ODA" in str(e)

    finally:
        shutil.rmtree(tmp_dir)


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
