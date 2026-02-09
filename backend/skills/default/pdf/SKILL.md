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

⚠️ **Important: Chinese Font Support**

reportlab's default fonts **do not support Chinese**, and will display as black blocks ▓▓▓. **You must register a Chinese font and explicitly specify fontName!**

#### Chinese Font Handling (Must Read)

**✅ Correct approach: Register font + Set ParagraphStyle**

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
import os

# 🔑 Step 1: Register Chinese font (required!)
font_paths = [
    '/System/Library/Fonts/PingFang.ttc',  # macOS
    '/System/Library/Fonts/STHeiti Light.ttc',  # macOS fallback
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
    'c:/windows/fonts/simsun.ttc',  # Windows
]

font_registered = False
for font_path in font_paths:
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
            font_registered = True
            print(f"✅ Successfully registered font: {font_path}")
            break
        except Exception as e:
            print(f"⚠️ Font {font_path} registration failed: {e}")
            continue

if not font_registered:
    raise Exception("❌ Cannot register Chinese font, please check font paths")

# 🔑 Step 2: Create styles using Chinese font
styles = getSampleStyleSheet()

# ⚠️ Note: fontName='ChineseFont' must be set, otherwise garbled text will still appear!
chinese_title = ParagraphStyle(
    'ChineseTitle',
    parent=styles['Title'],
    fontName='ChineseFont',  # 🔑 Key: specify font
    fontSize=18,
    leading=22,
    alignment=TA_LEFT
)

chinese_normal = ParagraphStyle(
    'ChineseNormal',
    parent=styles['Normal'],
    fontName='ChineseFont',  # 🔑 Key: specify font
    fontSize=12,
    leading=16,
    alignment=TA_LEFT
)

# 🔑 Step 3: Create content using custom styles
doc = SimpleDocTemplate("chinese.pdf", pagesize=A4)

story = [
    Paragraph("中文标题", chinese_title),
    Spacer(1, 12),
    Paragraph("这是中文内容，现在可以正常显示了。", chinese_normal),
    Paragraph("如果不设置 fontName，还是会显示黑色方块。", chinese_normal),
]

doc.build(story)
print("✅ Chinese PDF created successfully")
```

**❌ Wrong examples:**

```python
# ❌ Wrong: font not registered
styles = getSampleStyleSheet()
content = [Paragraph("中文", styles['Normal'])]  # Will show black blocks!

# ❌ Wrong: font registered but fontName not set in ParagraphStyle
pdfmetrics.registerFont(TTFont('ChineseFont', '/path/to/font.ttc'))
styles = getSampleStyleSheet()
content = [Paragraph("中文", styles['Normal'])]  # Will still show black blocks!

# ✅ Correct: register font + set fontName
pdfmetrics.registerFont(TTFont('ChineseFont', '/path/to/font.ttc'))
my_style = ParagraphStyle('MyStyle', fontName='ChineseFont', fontSize=12)
content = [Paragraph("中文", my_style)]  # Displays correctly
```

**Best Practices:**
1. ✅ **Must register font** - Use `pdfmetrics.registerFont(TTFont(...))`
2. ✅ **Must set fontName** - Specify `fontName='ChineseFont'` in `ParagraphStyle`
3. ✅ **Provide multiple font paths** - Compatible with different operating systems
4. ✅ **Add error handling** - Font loading may fail
5. ⚠️ **Note about .ttc fonts** - May contain multiple fonts, loads slower but usually works

#### Basic PDF Creation (English Only)
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text (English only without font registration)
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages (Chinese Support)
```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

# ✅ Use A4 instead of letter (better for internationalization)
doc = SimpleDocTemplate("report.pdf", pagesize=A4)
styles = getSampleStyleSheet()
story = []

# ⚠️ Note: Must register Chinese font and create styles using that font first
# See "Chinese Font Handling (Must Read)" section above

# Assuming font is already registered and chinese_title and chinese_normal styles are created
title = Paragraph("报告标题", chinese_title)  # Use Chinese style
story.append(title)
story.append(Spacer(1, 12))

# Chinese body text
body = Paragraph("这是报告的正文内容。可以包含中文、英文和数字。" * 10, chinese_normal)
story.append(body)
story.append(PageBreak())

# Second page
story.append(Paragraph("第二页标题", chinese_title))
story.append(Paragraph("第二页的内容", chinese_normal))

# Mixed Chinese and English
mixed = Paragraph("Mixed content: 中英文混合 123 ABC", chinese_normal)
story.append(mixed)

# Generate PDF
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
