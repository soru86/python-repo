# Webpage to Word Document Converter

A Python script that converts any webpage URL to a Microsoft Word document (.docx) while preserving styling, formatting, tables, fonts, and other elements.

## Features

- ✅ Converts webpage HTML to Word document format
- ✅ Preserves text formatting (bold, italic, underline)
- ✅ Preserves font sizes and families
- ✅ Preserves text colors
- ✅ Converts HTML tables to Word tables
- ✅ Handles headings (H1-H6)
- ✅ Converts lists (ordered and unordered)
- ✅ Preserves text alignment
- ✅ Automatically generates filename from URL

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script with a URL as an argument:

```bash
python webpage_to_word.py <URL> [OPTIONS]
```

### Basic Examples

```bash
# Basic usage
python webpage_to_word.py https://example.com

# URL without https:// (will be added automatically)
python webpage_to_word.py example.com

# Complex webpage
python webpage_to_word.py https://www.wikipedia.org/wiki/Python_(programming_language)
```

### Handling Authentication (403 Forbidden Errors)

For pages that require authentication (like Confluence, private wikis, etc.), you can use cookies or basic authentication:

#### Using Cookies (Recommended for Confluence)

**Option 1: Cookie string**
```bash
python webpage_to_word.py https://confluence.example.com/page \
  --cookies "JSESSIONID=abc123; atlassian.xsrf.token=xyz"
```

**Option 2: Cookies file**
1. Export cookies from your browser using extensions like "Cookie-Editor" or "EditThisCookie"
2. Save them in Netscape/Mozilla format
3. Use the file:
```bash
python webpage_to_word.py https://confluence.example.com/page \
  --cookies-file cookies.txt
```

#### Using Basic Authentication

```bash
# With username and password
python webpage_to_word.py https://example.com \
  --username myuser --password mypass

# Password will be prompted securely if omitted
python webpage_to_word.py https://example.com --username myuser
```

### Command-Line Options

- `--cookies`, `-c`: Cookie string (format: "name1=value1; name2=value2")
- `--cookies-file`, `-f`: Path to cookies file (Netscape/Mozilla format)
- `--username`, `-u`: Username for basic authentication
- `--password`, `-p`: Password for basic authentication
- `--help`, `-h`: Show help message

The script will:
1. Fetch the webpage content
2. Parse the HTML
3. Convert it to a Word document with preserved styling
4. Save it as a `.docx` file in the same directory as the script

The output filename is automatically generated from the URL (e.g., `example.com_index.docx`).

## Requirements

- Python 3.7 or higher
- Internet connection (to fetch webpages)

## Dependencies

- `requests` - For fetching webpage content
- `beautifulsoup4` - For parsing HTML
- `python-docx` - For creating Word documents
- `lxml` - HTML parser backend for BeautifulSoup

## Limitations

- Some complex CSS styling may not be fully preserved
- JavaScript-rendered content will not be captured (only static HTML)
- Images are not included in the conversion
- Some advanced HTML elements may be simplified

## Troubleshooting

### Common Issues

1. **403 Forbidden Error**
   - **Cause**: The page requires authentication or blocks automated requests
   - **Solution**: 
     - For Confluence/authenticated pages: Export cookies from your browser and use `--cookies` or `--cookies-file`
     - Log in to the website in your browser first, then export cookies
     - Use browser extensions like "Cookie-Editor" to export cookies
   
2. **Connection errors**
   - Make sure you have internet access and the URL is correct
   - Check if the URL is accessible in your browser
   
3. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Make sure you're using the correct Python version (3.7+)
   
4. **Permission errors**
   - Make sure you have write permissions in the script directory

### Exporting Cookies from Browser

**Chrome/Edge:**
1. Install extension: "Cookie-Editor" or "EditThisCookie"
2. Open the webpage you want to convert
3. Click the extension icon
4. Export cookies (choose Netscape format for file, or copy as string)

**Firefox:**
1. Install extension: "Cookie-Editor"
2. Open the webpage
3. Export cookies in Netscape format

**Safari:**
1. Use Developer menu → Show Web Inspector
2. Storage tab → Cookies
3. Export manually or use a cookie export extension

