"""
PDF to EMF Converter

Converts PDF pages to EMF (Enhanced Metafile) via SVG intermediate.
Requires Inkscape (https://inkscape.org/) for the SVG → EMF step.

Architecture:
    PDF → PyMuPDF (SVG) → temp .svg → Inkscape CLI → EMF file

Inkscape 1.x syntax: inkscape --export-type=emf --export-filename=out.emf in.svg
EMF is a Windows vector metafile format supported natively by Visio, Word, and AutoCAD.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import pymupdf

# Common Inkscape installation paths
_INKSCAPE_CANDIDATES = [
    "inkscape",
    r"C:\Program Files\Inkscape\bin\inkscape.exe",
    r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
    "/usr/bin/inkscape",
    "/usr/local/bin/inkscape",
    "/Applications/Inkscape.app/Contents/MacOS/inkscape",
]


def _find_inkscape() -> Optional[str]:
    """Locate the Inkscape executable on PATH or in common install locations."""
    for candidate in _INKSCAPE_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
        if os.path.isfile(candidate):
            return candidate
    return None


def inkscape_path() -> Optional[str]:
    """Return the Inkscape executable path, or None if not installed."""
    return _find_inkscape()


class PDFtoEMFConverter:
    """
    Converts PDF pages to EMF (Enhanced Metafile) format.

    Requires Inkscape. Install from https://inkscape.org/ and ensure
    the ``inkscape`` binary is on your PATH.

    EMF is the recommended vector import format for Microsoft Visio and
    Microsoft Office on Windows.
    """

    def __init__(self, pdf_path: str) -> None:
        """
        Initialize converter.

        Args:
            pdf_path: Path to input PDF file.

        Raises:
            FileNotFoundError: If the PDF does not exist.
            RuntimeError: If Inkscape is not installed/findable.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf_path = pdf_path

        self._inkscape = _find_inkscape()
        if not self._inkscape:
            raise RuntimeError(
                "Inkscape is required for EMF conversion.\n"
                "Install from https://inkscape.org/ and ensure 'inkscape' is on PATH.\n"
                "After install, verify with: inkscape --version"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, output_path: str, page: int = 0) -> str:
        """
        Convert one PDF page to an EMF file.

        Args:
            output_path: Destination .emf file path.
            page: Page index (0-based).

        Returns:
            Absolute path to the written EMF file.

        Raises:
            ValueError: If page is out of range.
            RuntimeError: If Inkscape conversion fails.
        """
        svg_bytes = self._page_to_svg(page)

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            tmp.write(svg_bytes)
            tmp_svg = tmp.name

        try:
            self._inkscape_convert(tmp_svg, output_path)
        finally:
            os.unlink(tmp_svg)

        if not os.path.exists(output_path):
            raise RuntimeError(
                f"Inkscape did not produce output at {output_path}. "
                "Check Inkscape version supports EMF export."
            )

        return os.path.abspath(output_path)

    def convert_all_pages(self, output_dir: str) -> List[str]:
        """
        Convert every page to a separate EMF file.

        Args:
            output_dir: Directory for output files.

        Returns:
            List of absolute paths to created EMF files.
        """
        doc = pymupdf.open(self.pdf_path)
        page_count = doc.page_count
        doc.close()

        os.makedirs(output_dir, exist_ok=True)
        stem = Path(self.pdf_path).stem
        output_files = []

        for i in range(page_count):
            out_path = os.path.join(output_dir, f"{stem}_page_{i + 1}.emf")
            self.convert(out_path, page=i)
            output_files.append(os.path.abspath(out_path))

        return output_files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _page_to_svg(self, page: int) -> bytes:
        """Render a PDF page to SVG bytes via PyMuPDF."""
        doc = pymupdf.open(self.pdf_path)
        if page >= doc.page_count:
            doc.close()
            raise ValueError(
                f"Page {page} is out of range (PDF has {doc.page_count} pages)"
            )
        page_obj = doc.load_page(page)
        svg_data = page_obj.get_svg_image()
        doc.close()
        if isinstance(svg_data, str):
            svg_data = svg_data.encode("utf-8")
        return svg_data

    def _inkscape_convert(self, svg_path: str, emf_path: str) -> None:
        """Call Inkscape to convert an SVG file to EMF."""
        result = subprocess.run(
            [
                self._inkscape,
                "--export-type=emf",
                f"--export-filename={emf_path}",
                svg_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Inkscape exited with code {result.returncode}.\n"
                f"stderr: {result.stderr.strip()}"
            )
