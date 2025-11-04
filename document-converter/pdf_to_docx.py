#!/usr/bin/env python3
"""
PDF to DOCX Converter Utility

This utility converts PDF files to DOCX format while preserving complex formatting
including fonts, tables, colors, and other document elements.

Usage:
    python pdf_to_docx.py <pdf_file_path>
    
Example:
    python pdf_to_docx.py /path/to/document.pdf
"""

import os
import sys
import argparse
from pathlib import Path

# Monkey patch to fix PyMuPDF compatibility issue
# PyMuPDF 1.26+ removed get_area() method, use area property instead
try:
    import fitz  # PyMuPDF
    if hasattr(fitz, 'Rect') and not hasattr(fitz.Rect, 'get_area'):
        # Add get_area method for compatibility with pdf2docx
        def get_area(self):
            return self.width * self.height
        fitz.Rect.get_area = get_area
except ImportError:
    pass  # PyMuPDF not installed yet, will be handled later


def validate_pdf_file(pdf_path):
    """
    Validate that the PDF file exists and has the correct extension.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Path: Path object if valid
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is not a PDF
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    return pdf_path


def convert_pdf_to_docx(pdf_path, docx_path=None):
    """
    Convert PDF file to DOCX format while preserving formatting.
    
    Args:
        pdf_path (Path): Path to the input PDF file
        docx_path (Path, optional): Path to the output DOCX file.
                                   If None, uses the same name as PDF with .docx extension
        
    Returns:
        Path: Path to the generated DOCX file
        
    Raises:
        ImportError: If pdf2docx library is not installed
        Exception: If conversion fails
    """
    try:
        from pdf2docx import parse, Converter
    except ImportError:
        raise ImportError(
            "pdf2docx library is not installed. "
            "Please install it using: pip install pdf2docx"
        )
    
    # Generate output path if not provided
    if docx_path is None:
        docx_path = pdf_path.with_suffix('.docx')
    else:
        docx_path = Path(docx_path)
    
    print(f"Converting PDF to DOCX...")
    print(f"Input:  {pdf_path}")
    print(f"Output: {docx_path}")
    
    try:
        # Try using the parse function first (simpler and more stable)
        parse(str(pdf_path), str(docx_path))
        
        print(f"\n✓ Conversion completed successfully!")
        print(f"  DOCX file saved at: {docx_path}")
        
        return docx_path
        
    except Exception as parse_error:
        # If parse fails, try the Converter method as fallback
        try:
            print("Trying alternative conversion method...")
            cv = Converter(str(pdf_path))
            cv.convert(str(docx_path), start=0, end=None)
            cv.close()
            
            print(f"\n✓ Conversion completed successfully!")
            print(f"  DOCX file saved at: {docx_path}")
            
            return docx_path
            
        except Exception as converter_error:
            # If both methods fail, raise the original error
            raise Exception(f"Conversion failed: {str(parse_error)}")


def main():
    """Main function to handle command-line arguments and execute conversion."""
    parser = argparse.ArgumentParser(
        description='Convert PDF files to DOCX format while preserving formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pdf_to_docx.py document.pdf
  python3 pdf_to_docx.py /path/to/document.pdf
  python3 pdf_to_docx.py document.pdf --output custom_name.docx
        """
    )
    
    parser.add_argument(
        'pdf_file',
        type=str,
        help='Path to the PDF file to convert'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Optional output DOCX file path. If not specified, uses the same name as PDF with .docx extension'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate PDF file
        pdf_path = validate_pdf_file(args.pdf_file)
        
        # Convert to DOCX
        docx_path = convert_pdf_to_docx(pdf_path, args.output)
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nTo install the required library, run:", file=sys.stderr)
        print("  pip install pdf2docx", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

