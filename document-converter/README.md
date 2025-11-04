# PDF to DOCX Converter

A Python utility that converts PDF files to DOCX format while preserving complex formatting including fonts, tables, colors, and other document elements.

## Features

- ✅ Preserves fonts, tables, colors, and formatting
- ✅ Handles complex PDF layouts
- ✅ Simple command-line interface
- ✅ Automatic output file naming
- ✅ Error handling and validation

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install pdf2docx
```

## Usage

### Basic Usage

Convert a PDF file to DOCX (output will be saved with the same name in the same location):

```bash
python3 pdf_to_docx.py document.pdf
```

### With Full Path

```bash
python3 pdf_to_docx.py /path/to/document.pdf
```

### Custom Output Path

```bash
python3 pdf_to_docx.py document.pdf --output custom_name.docx
```

or

```bash
python3 pdf_to_docx.py document.pdf -o custom_name.docx
```

## Examples

```bash
# Convert a PDF in the current directory
python3 pdf_to_docx.py report.pdf
# Output: report.docx (in the same directory)

# Convert with full path
python3 pdf_to_docx.py ~/Documents/invoice.pdf
# Output: ~/Documents/invoice.docx

# Specify custom output name
python3 pdf_to_docx.py report.pdf -o converted_report.docx
```

## Requirements

- Python 3.6 or higher
- pdf2docx library (see requirements.txt)

## How It Works

The utility uses the `pdf2docx` library, which:
- Parses PDF structure and layout
- Extracts text, tables, images, and formatting
- Reconstructs the document in DOCX format
- Preserves fonts, colors, tables, and other formatting elements

## Notes

- The conversion quality depends on the PDF structure. Well-structured PDFs with text layers will convert better than scanned/image-based PDFs.
- Large PDF files may take some time to process.
- Complex formatting may not always be perfectly preserved, but the utility makes its best effort to maintain the original appearance.

## Error Handling

The utility provides clear error messages for:
- Missing PDF files
- Invalid file types
- Missing dependencies
- Conversion failures

