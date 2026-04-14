# PDF to Visio Converter

A local Python library for converting PDF engineering drawings to Visio-compatible formats.

## Installation

```bash
pip install pymupdf
```

## Quick Start

```python
from pdf_to_visio import PDFConverter

converter = PDFConverter("drawing.pdf")
converter.to_svg("output_dir/")
converter.to_svg_single("page_1.svg", page=0)
```

## Architecture

```
PDF Input → PyMuPDF (extract vectors/text) → SVG Output → Visio Import
```

## Features

- Vector graphics preservation
- Text extraction with positioning
- Multi-page PDF support
- Batch conversion
- Engineering drawing support

## Testing

```bash
pytest tests/ -v
```

## License

MIT