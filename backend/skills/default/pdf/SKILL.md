---
name: pdf
description: Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see reference.md. If you need to fill out a PDF form, read forms.md and follow its instructions.

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine all tables
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

> **⚠️ CRITICAL: CJK (Chinese/Japanese/Korean) Font Support**
> 
> The default reportlab fonts do NOT support CJK characters. If your content contains **any** Chinese, Japanese, or Korean text, you **MUST** register a CJK font first. Failing to do so will result in garbled text or missing characters in the output PDF.

#### CJK Font Registration (REQUIRED for Chinese/Japanese/Korean content)

**IMPORTANT: Always call `register_cjk_fonts()` before creating any PDF that may contain CJK text.**

```python
import os
import glob
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.fonts import addMapping

# --- CJK font name constant (use this everywhere in your code) ---
CJK_FONT_NAME = "ChineseSans"  # Will be registered below

def register_cjk_fonts():
    """Register CJK fonts for reportlab. Call this ONCE before creating any PDF."""
    global CJK_FONT_NAME
    
    # Try to find system CJK fonts in common locations
    font_search_paths = [
        # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Microsoft/msyh.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux (Docker / Ubuntu / Debian)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    
    # Also search common font directories recursively for CJK fonts
    font_dirs = [
        "/usr/share/fonts",
        "/System/Library/Fonts",
        "/Library/Fonts",
    ]
    for font_dir in font_dirs:
        if os.path.isdir(font_dir):
            for ext in ("*.ttf", "*.ttc", "*.otf"):
                for path in glob.glob(os.path.join(font_dir, "**", ext), recursive=True):
                    name_lower = os.path.basename(path).lower()
                    if any(kw in name_lower for kw in ("noto", "cjk", "wqy", "hei", "song", "ming", "gothic", "ping")):
                        font_search_paths.append(path)
    
    for font_path in font_search_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(CJK_FONT_NAME, font_path))
                # Also register bold/italic variants using the same font
                pdfmetrics.registerFont(TTFont(f"{CJK_FONT_NAME}-Bold", font_path))
                addMapping(CJK_FONT_NAME, 0, 0, CJK_FONT_NAME)       # normal
                addMapping(CJK_FONT_NAME, 1, 0, f"{CJK_FONT_NAME}-Bold")  # bold
                addMapping(CJK_FONT_NAME, 0, 1, CJK_FONT_NAME)       # italic
                addMapping(CJK_FONT_NAME, 1, 1, f"{CJK_FONT_NAME}-Bold")  # bold-italic
                print(f"Registered CJK font: {font_path}")
                return True
            except Exception as e:
                print(f"Failed to register font {font_path}: {e}")
                continue
    
    # Fallback: use reportlab built-in CID font (less pretty but works)
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        CJK_FONT_NAME = "STSong-Light"
        print("Registered fallback CID font: STSong-Light")
        return True
    except Exception:
        pass
    
    print("WARNING: No CJK fonts found. Chinese text may not render correctly.")
    return False


def get_cjk_styles():
    """Get reportlab styles with CJK font applied to all text styles."""
    styles = getSampleStyleSheet()
    
    # Override all standard styles with CJK font
    for style_name in ['Normal', 'BodyText', 'Italic', 'Title', 'Heading1', 
                        'Heading2', 'Heading3', 'Heading4', 'Heading5', 'Heading6',
                        'Bullet', 'Definition', 'Code', 'UnorderedList', 'OrderedList']:
        if style_name in styles:
            styles[style_name].fontName = CJK_FONT_NAME
    
    return styles
```

#### Usage Example - PDF with Chinese Text
```python
# ALWAYS register CJK fonts first!
register_cjk_fonts()

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

# Use CJK-enabled styles
styles = get_cjk_styles()

doc = SimpleDocTemplate("chinese_report.pdf", pagesize=A4)
story = []

story.append(Paragraph("学术论文标题", styles['Title']))
story.append(Spacer(1, 12))
story.append(Paragraph("这是正文内容。中文字符可以正常显示。", styles['Normal']))

doc.build(story)
```

#### Basic PDF Creation (English only)
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

# NOTE: If your content contains Chinese/Japanese/Korean text,
# replace getSampleStyleSheet() with get_cjk_styles() and 
# call register_cjk_fonts() first! See CJK section above.

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Page 2
story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

# Build PDF
doc.build(story)
```

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Extract Text from Scanned PDFs
```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
images = convert_from_path('scanned.pdf')

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"

print(text)
```

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# This extracts all images as output_prefix-000.jpg, output_prefix-001.jpg, etc.
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pdf-lib or pypdf (see forms.md) | See forms.md |

## Next Steps

- For advanced pypdfium2 usage, see reference.md
- For JavaScript libraries (pdf-lib), see reference.md
- If you need to fill out a PDF form, follow the instructions in forms.md
- For troubleshooting guides, see reference.md
