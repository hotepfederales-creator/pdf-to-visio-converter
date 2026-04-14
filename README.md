# PDF to Visio / CAD Converter

Convert PDF engineering drawings to SVG, DXF, EMF, and DWG formats.

## Installation

```bash
pip install pymupdf          # SVG output (always required)
pip install ezdxf            # DXF/DWG output
# EMF: install Inkscape → https://inkscape.org/
# DWG: install ODA File Converter → https://www.opendesign.com/guestfiles/oda_file_converter
```

## Quick Start

```python
from pdf_to_visio import convert_to_format

# SVG — no external tools needed
convert_to_format("drawing.pdf", "output/", fmt="svg")

# DXF — requires ezdxf
convert_to_format("drawing.pdf", "output/", fmt="dxf")

# EMF — requires Inkscape on PATH
convert_to_format("drawing.pdf", "output/", fmt="emf")

# DWG — requires ODA File Converter on PATH
convert_to_format("drawing.pdf", "output/", fmt="dwg")

# Single page, specific version
convert_to_format("drawing.pdf", "output/", fmt="dxf", page=0, dxf_version="R2018")
```

## Format Details

| Format | Class | Requires | Use case |
|--------|-------|----------|----------|
| SVG | `PDFConverter` | pymupdf only | Visio, browsers, universal |
| DXF | `PDFtoDXFConverter` | ezdxf | AutoCAD, LibreCAD, BricsCAD |
| EMF | `PDFtoEMFConverter` | Inkscape | Visio, Word, Windows native |
| DWG | `PDFtoDWGConverter` | ODA File Converter | AutoCAD native binary |

## Architecture

```
PDF → PyMuPDF (extract paths + text)
         ├── SVG  → direct via get_svg_image()
         ├── DXF  → ezdxf (LWPOLYLINE + TEXT entities)
         ├── EMF  → SVG → Inkscape CLI
         └── DWG  → DXF → ODA File Converter
```

## Testing

```bash
pytest tests/ -v
```

15 tests covering SVG, DXF (entities, text, multi-page, version validation),
EMF/DWG dependency detection, and the unified `convert_to_format()` API.

## License

MIT