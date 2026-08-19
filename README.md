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

# Excel wire list → Visio-importable harness SVG
from pdf_to_visio import convert_excel_to_visio
convert_excel_to_visio("wire-list.xlsx", "output/harness.svg")

# Excel wire list → native Visio file, when Visio + pywin32 are installed
convert_excel_to_visio("wire-list.xlsx", "output/harness.vsdx")
```

## Format Details

| Format | Class | Requires | Use case |
|--------|-------|----------|----------|
| SVG | `PDFConverter` | pymupdf only | Visio, browsers, universal |
| DXF | `PDFtoDXFConverter` | ezdxf | AutoCAD, LibreCAD, BricsCAD |
| EMF | `PDFtoEMFConverter` | Inkscape | Visio, Word, Windows native |
| DWG | `PDFtoDWGConverter` | ODA File Converter | AutoCAD native binary |
| SVG/VSDX harness | `convert_excel_to_visio` | openpyxl; pywin32 + Visio for VSDX | Wire harness / breakout drawings from Excel |

## Architecture

```
PDF → PyMuPDF (extract paths + text)
         ├── SVG  → direct via get_svg_image()
         ├── DXF  → ezdxf (LWPOLYLINE + TEXT entities)
         ├── EMF  → SVG → Inkscape CLI
         └── DWG  → DXF → ODA File Converter

Excel wire list → normalized source/destination pins
                ├── SVG  → Visio-importable harness drawing
                └── VSDX → SVG imported through Visio COM automation
```

## Excel Wire List Format

The Excel mapper accepts common header aliases. Required logical columns:

| Required | Common aliases |
|----------|----------------|
| Source connector | `From Connector`, `Source Connector`, `Src Connector` |
| Source pin | `From Pin`, `Source Pin`, `Src Pin` |
| Destination connector | `To Connector`, `Destination Connector`, `Dest Connector` |
| Destination pin | `To Pin`, `Destination Pin`, `Dest Pin` |

Optional columns: `Signal`, `Wire Color`, `AWG`/`Gauge`, `Breakout Jack`/`Test Point`.

CLI:

```bash
excel2visio wire-list.xlsx output/harness.svg --sheet Harness --title "Bench Harness"
excel2visio wire-list.xlsx output/harness.vsdx  # requires Microsoft Visio + pywin32
```

## Visio Template Pack

`visio_templates/` contains SVG templates you can import into Visio and edit:

- `harness-overview.svg`
- `breakout-box-front-panel.svg`
- `connector-pinout.svg`

## Testing

```bash
pytest tests/ -v
```

20 tests covering SVG, lazy optional-dependency imports, page validation,
Excel wire-list mapping, DXF (entities, text, multi-page, version validation),
EMF/DWG dependency detection, and the unified `convert_to_format()` API.

## License

MIT