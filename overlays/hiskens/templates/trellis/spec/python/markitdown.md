# MarkItDown Document Conversion Guidelines

> Convert files (PDF, DOCX, XLSX, CSV, HTML etc.) to Markdown using Microsoft MarkItDown.

## Overview

MarkItDown converts various document formats to clean Markdown text. Useful for:
- Converting 台账 Excel files to LLM-friendly text
- Extracting text from PDF reports
- Batch converting project documents for analysis

## Installation

```bash
uv add 'markitdown[all]'

# Or specific formats only
uv add 'markitdown[pdf,docx,xlsx]'
```

## Supported Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text extraction, table detection |
| Word | `.docx` | Tables, headings, formatting preserved |
| Excel | `.xlsx`, `.xls` | Sheets → Markdown tables |
| PowerPoint | `.pptx` | Slides with notes |
| CSV | `.csv` | Automatic table conversion |
| HTML | `.html` | Clean conversion |
| JSON | `.json` | Structured representation |
| XML | `.xml` | Structured format |
| Images | `.jpg`, `.png` | EXIF metadata + OCR |
| ZIP | `.zip` | Iterates contents |

## Python API

### Basic Conversion

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("data/台账.xlsx")
print(result.text_content)  # Markdown text
print(result.title)         # Document title (if available)
```

### Stream Conversion (large files)

```python
with open("report.pdf", "rb") as f:
    result = md.convert_stream(f, file_extension=".pdf")
    print(result.text_content)
```

**Note**: Stream must be binary mode (`"rb"`), not text mode.

### Batch Conversion

```python
from markitdown import MarkItDown
from pathlib import Path

md = MarkItDown()

input_dir = Path("data/reports/")
output_dir = Path("data/markdown/")
output_dir.mkdir(exist_ok=True)

for pdf_file in input_dir.glob("*.pdf"):
    result = md.convert(str(pdf_file))
    output = output_dir / f"{pdf_file.stem}.md"
    output.write_text(result.text_content)
```

### Parallel Batch Conversion

```python
from concurrent.futures import ThreadPoolExecutor

md = MarkItDown()

def convert_file(filepath):
    return filepath, md.convert(str(filepath))

files = list(Path("data/").glob("*.xlsx"))
with ThreadPoolExecutor(max_workers=4) as executor:
    for filepath, result in executor.map(lambda f: convert_file(f), files):
        Path(f"output/{filepath.stem}.md").write_text(result.text_content)
```

## Command-Line Usage

```bash
# Basic conversion
markitdown document.pdf > output.md

# Specify output file
markitdown document.pdf -o output.md

# Pipe
cat report.pdf | markitdown > output.md
```

## Project-Specific Patterns

### Convert Excel 台账 to Markdown

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("data/设备台账.xlsx")

# Result contains Markdown tables for each sheet
with open("data/台账_text.md", "w", encoding="utf-8") as f:
    f.write(result.text_content)
```

### Extract Text from PDF Reports

```python
md = MarkItDown()
result = md.convert("reports/可靠性分析报告.pdf")

# Use extracted text for further processing
report_text = result.text_content
```

### Convert Multiple Format Types

```python
from markitdown import MarkItDown
from pathlib import Path

md = MarkItDown()
extensions = [".pdf", ".docx", ".xlsx"]

for ext in extensions:
    for f in Path("data/").glob(f"*{ext}"):
        result = md.convert(str(f))
        Path(f"output/{f.stem}.md").write_text(result.text_content)
```

## Performance Tips

1. **Reuse `MarkItDown` instance** — create once, convert many
2. **Use `convert_stream()`** for large files — avoids loading full file
3. **Use `ThreadPoolExecutor`** for batch conversion — parallel I/O
4. **Install only needed formats** — `markitdown[pdf,xlsx]` instead of `markitdown[all]`

## Caveats

- Complex PDF layouts may not preserve perfect formatting
- Scanned PDFs require OCR (tesseract): `sudo apt install tesseract-ocr`
- Excel formulas are converted to calculated values, not formula text
- Chinese characters in filenames work but test on your OS
- Requires Python >= 3.10
