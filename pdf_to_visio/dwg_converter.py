"""
PDF to DWG Converter

Converts PDF pages to DWG (AutoCAD native binary format) via DXF intermediate.

Architecture:
    PDF → PDFtoDXFConverter → temp .dxf → ODA File Converter → .dwg

DWG is Autodesk's proprietary binary format. No Python library can write
DWG natively; the ODA File Converter (free, from Open Design Alliance)
is the most reliable cross-platform DXF→DWG bridge.

Download ODA File Converter:
    https://www.opendesign.com/guestfiles/oda_file_converter

Supported DWG output versions:
    ACAD9, ACAD10, ACAD12, ACAD14, ACAD2000, ACAD2004, ACAD2007,
    ACAD2010, ACAD2013, ACAD2018  (default: ACAD2018)
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from .dxf_converter import PDFtoDXFConverter

# Common ODA File Converter installation paths
_ODA_CANDIDATES = [
    "ODAFileConverter",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    "/usr/bin/ODAFileConverter",
    "/opt/ODA/ODAFileConverter",
    "/usr/local/bin/ODAFileConverter",
]

SUPPORTED_DWG_VERSIONS = (
    "ACAD9",
    "ACAD10",
    "ACAD12",
    "ACAD14",
    "ACAD2000",
    "ACAD2004",
    "ACAD2007",
    "ACAD2010",
    "ACAD2013",
    "ACAD2018",
)


def _find_oda() -> Optional[str]:
    """Locate the ODA File Converter executable."""
    for candidate in _ODA_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
        if os.path.isfile(candidate):
            return candidate
    return None


def oda_converter_path() -> Optional[str]:
    """Return the ODA File Converter path, or None if not installed."""
    return _find_oda()


class PDFtoDWGConverter:
    """
    Converts PDF pages to DWG (AutoCAD native format).

    Requires ODA File Converter (free).
    Download: https://www.opendesign.com/guestfiles/oda_file_converter

    DWG is produced via a DXF intermediate:
        PDF → DXF (via ezdxf) → DWG (via ODA File Converter)
    """

    def __init__(self, pdf_path: str) -> None:
        """
        Initialize converter.

        Args:
            pdf_path: Path to input PDF file.

        Raises:
            FileNotFoundError: If the PDF does not exist.
            RuntimeError: If ODA File Converter is not installed/findable.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf_path = pdf_path

        self._oda = _find_oda()
        if not self._oda:
            raise RuntimeError(
                "ODA File Converter is required for DWG output.\n"
                "Download free from: https://www.opendesign.com/guestfiles/oda_file_converter\n"
                "After install, ensure 'ODAFileConverter' is on your PATH."
            )

        self._dxf_converter = PDFtoDXFConverter(pdf_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        output_path: str,
        page: int = 0,
        dwg_version: str = "ACAD2018",
    ) -> str:
        """
        Convert one PDF page to a DWG file.

        Args:
            output_path: Destination .dwg file path.
            page: Page index (0-based).
            dwg_version: Target DWG version. One of SUPPORTED_DWG_VERSIONS.

        Returns:
            Absolute path to the written DWG file.

        Raises:
            ValueError: If page is out of range or dwg_version is unknown.
            RuntimeError: If ODA conversion fails.
        """
        if dwg_version not in SUPPORTED_DWG_VERSIONS:
            raise ValueError(
                f"Unknown DWG version '{dwg_version}'. "
                f"Choose from: {', '.join(SUPPORTED_DWG_VERSIONS)}"
            )

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Step 1: PDF → DXF
            dxf_path = os.path.join(tmp_dir, "page.dxf")
            self._dxf_converter.convert(dxf_path, page=page)

            # Step 2: DXF → DWG via ODA
            # ODA CLI: ODAFileConverter <input_dir> <output_dir> <ver> <type> <recurse> <audit>
            result = subprocess.run(
                [self._oda, tmp_dir, tmp_dir, dwg_version, "DWG", "0", "1"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            dwg_tmp = os.path.join(tmp_dir, "page.dwg")
            if not os.path.exists(dwg_tmp):
                raise RuntimeError(
                    f"ODA File Converter did not produce a DWG file.\n"
                    f"Exit code: {result.returncode}\n"
                    f"stderr: {result.stderr.strip()}"
                )

            shutil.move(dwg_tmp, output_path)

        return os.path.abspath(output_path)

    def convert_all_pages(
        self,
        output_dir: str,
        dwg_version: str = "ACAD2018",
    ) -> List[str]:
        """
        Convert every page to a separate DWG file.

        Args:
            output_dir: Directory for output files.
            dwg_version: Target DWG version.

        Returns:
            List of absolute paths to created DWG files.
        """
        from pymupdf import open as pdf_open

        doc = pdf_open(self.pdf_path)
        page_count = doc.page_count
        doc.close()

        os.makedirs(output_dir, exist_ok=True)
        stem = Path(self.pdf_path).stem
        output_files = []

        for i in range(page_count):
            out_path = os.path.join(output_dir, f"{stem}_page_{i + 1}.dwg")
            self.convert(out_path, page=i, dwg_version=dwg_version)
            output_files.append(os.path.abspath(out_path))

        return output_files
