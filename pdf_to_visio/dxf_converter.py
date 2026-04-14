"""
PDF to DXF Converter

Converts PDF engineering drawings to DXF (AutoCAD Drawing Exchange Format).
Uses PyMuPDF to extract vector paths and text, then writes DXF via ezdxf.

Architecture:
    PDF → PyMuPDF (paths + text) → ezdxf entities → DXF file

Bezier curves are approximated with 16-segment polylines (sufficient for
most engineering tolerances; increase BEZIER_SEGMENTS for finer curves).
"""

import os
from pathlib import Path
from typing import List, Tuple

import pymupdf

try:
    import ezdxf
    from ezdxf.math import Vec3
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ezdxf is required for DXF conversion: pip install ezdxf"
    ) from exc

BEZIER_SEGMENTS = 16  # segments per cubic bezier approximation


def _cubic_bezier_points(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    n: int = BEZIER_SEGMENTS,
) -> List[Tuple[float, float]]:
    """Approximate a cubic bezier curve with n line segments."""
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _flip_y(y: float, page_height: float) -> float:
    """Convert from PyMuPDF top-down Y to DXF bottom-up Y."""
    return page_height - y


class PDFtoDXFConverter:
    """
    Converts PDF pages to DXF format.

    Extracts:
    - Lines, rectangles, and bezier curves → LWPOLYLINE entities
    - Text spans with position and size → TEXT entities

    DWG version defaults to 'R2010' (AutoCAD 2010), compatible with
    AutoCAD 2010+, BricsCAD, LibreCAD, and most modern CAD tools.
    """

    SUPPORTED_VERSIONS = ("R12", "R2000", "R2004", "R2007", "R2010", "R2013", "R2018")

    def __init__(self, pdf_path: str) -> None:
        """
        Initialize converter.

        Args:
            pdf_path: Path to input PDF file.

        Raises:
            FileNotFoundError: If the PDF does not exist.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf_path = pdf_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        output_path: str,
        page: int = 0,
        dxf_version: str = "R2010",
    ) -> str:
        """
        Convert one PDF page to a DXF file.

        Args:
            output_path: Destination .dxf file path.
            page: Page index (0-based).
            dxf_version: DXF format version. One of SUPPORTED_VERSIONS.

        Returns:
            Absolute path to the written DXF file.

        Raises:
            ValueError: If page is out of range or dxf_version is unknown.
        """
        if dxf_version not in self.SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unknown DXF version '{dxf_version}'. "
                f"Choose from: {', '.join(self.SUPPORTED_VERSIONS)}"
            )

        doc = pymupdf.open(self.pdf_path)
        if page >= doc.page_count:
            doc.close()
            raise ValueError(
                f"Page {page} is out of range (PDF has {doc.page_count} pages)"
            )

        page_obj = doc.load_page(page)
        page_height = page_obj.rect.height

        dxf_doc = ezdxf.new(dxf_version)
        msp = dxf_doc.modelspace()

        self._add_drawings(msp, page_obj, page_height)
        self._add_text(msp, page_obj, page_height)

        doc.close()

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        dxf_doc.saveas(output_path)
        return os.path.abspath(output_path)

    def convert_all_pages(
        self,
        output_dir: str,
        dxf_version: str = "R2010",
    ) -> List[str]:
        """
        Convert every page to a separate DXF file.

        Args:
            output_dir: Directory for output files.
            dxf_version: DXF format version.

        Returns:
            List of absolute paths to created DXF files.
        """
        doc = pymupdf.open(self.pdf_path)
        page_count = doc.page_count
        doc.close()

        os.makedirs(output_dir, exist_ok=True)
        stem = Path(self.pdf_path).stem
        output_files = []

        for i in range(page_count):
            out_path = os.path.join(output_dir, f"{stem}_page_{i + 1}.dxf")
            self.convert(out_path, page=i, dxf_version=dxf_version)
            output_files.append(os.path.abspath(out_path))

        return output_files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_drawings(self, msp, page_obj, page_height: float) -> None:
        """Convert vector paths from PDF page to DXF LWPOLYLINE entities."""
        for path in page_obj.get_drawings():
            poly_pts: List[Tuple[float, float]] = []

            for item in path.get("items", []):
                kind = item[0]

                if kind == "l":  # straight line
                    p1 = (item[1].x, _flip_y(item[1].y, page_height))
                    p2 = (item[2].x, _flip_y(item[2].y, page_height))
                    if poly_pts and poly_pts[-1] != p1:
                        self._flush_poly(msp, poly_pts)
                        poly_pts = [p1]
                    elif not poly_pts:
                        poly_pts = [p1]
                    poly_pts.append(p2)

                elif kind == "c":  # cubic bezier
                    ctrl = [
                        (item[j].x, _flip_y(item[j].y, page_height))
                        for j in range(1, 5)
                    ]
                    pts = _cubic_bezier_points(*ctrl)
                    if poly_pts and poly_pts[-1] != pts[0]:
                        self._flush_poly(msp, poly_pts)
                        poly_pts = list(pts)
                    elif not poly_pts:
                        poly_pts = list(pts)
                    else:
                        poly_pts.extend(pts[1:])

                elif kind == "re":  # axis-aligned rectangle
                    self._flush_poly(msp, poly_pts)
                    poly_pts = []
                    rect = item[1]
                    corners = [
                        (rect.x0, _flip_y(rect.y0, page_height)),
                        (rect.x1, _flip_y(rect.y0, page_height)),
                        (rect.x1, _flip_y(rect.y1, page_height)),
                        (rect.x0, _flip_y(rect.y1, page_height)),
                    ]
                    msp.add_lwpolyline(corners, close=True)

                elif kind == "qu":  # quadrilateral
                    self._flush_poly(msp, poly_pts)
                    poly_pts = []
                    quad = item[1]
                    corners = [
                        (quad.ul.x, _flip_y(quad.ul.y, page_height)),
                        (quad.ur.x, _flip_y(quad.ur.y, page_height)),
                        (quad.lr.x, _flip_y(quad.lr.y, page_height)),
                        (quad.ll.x, _flip_y(quad.ll.y, page_height)),
                    ]
                    msp.add_lwpolyline(corners, close=True)

            self._flush_poly(msp, poly_pts)

    def _flush_poly(
        self, msp, pts: List[Tuple[float, float]]
    ) -> None:
        """Write a polyline to modelspace if it has at least 2 points."""
        if len(pts) >= 2:
            msp.add_lwpolyline(pts)
        pts.clear()

    def _add_text(self, msp, page_obj, page_height: float) -> None:
        """Convert PDF text spans to DXF TEXT entities."""
        text_dict = page_obj.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text, 1 = image
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    origin = span.get("origin", (0, 0))
                    x = origin[0]
                    y = _flip_y(origin[1], page_height)
                    size = span.get("size", 12)
                    msp.add_text(
                        text,
                        dxfattribs={"height": size, "insert": Vec3(x, y, 0)},
                    )
