#!/usr/bin/env python3
"""
CJK (Chinese/Japanese/Korean) font registration helper for reportlab.

This module provides automatic CJK font detection and registration for
generating PDFs with Chinese, Japanese, or Korean text using reportlab.

Usage:
    from cjk_fonts import register_cjk_fonts, get_cjk_styles, CJK_FONT_NAME
    
    # Register fonts (call once at start)
    register_cjk_fonts()
    
    # Get styles with CJK font applied
    styles = get_cjk_styles()
    
    # Use in your PDF generation
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    doc = SimpleDocTemplate("output.pdf")
    story = [Paragraph("中文标题", styles['Title'])]
    doc.build(story)
"""

import os
import glob

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.fonts import addMapping

# Global font name - use this in your code
CJK_FONT_NAME = "ChineseSans"

_fonts_registered = False


def register_cjk_fonts() -> bool:
    """Register CJK fonts for reportlab. Call this ONCE before creating any PDF.
    
    Returns:
        True if a CJK font was successfully registered, False otherwise.
    """
    global CJK_FONT_NAME, _fonts_registered
    
    if _fonts_registered:
        return True
    
    # Known CJK font paths in common locations
    font_search_paths = [
        # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Microsoft/msyh.ttf",
        "/Library/Fonts/Microsoft/simsun.ttf",
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
        "C:/Windows/Fonts/simhei.ttf",
    ]
    
    # Also search common font directories recursively for CJK fonts
    font_dirs = ["/usr/share/fonts", "/System/Library/Fonts", "/Library/Fonts"]
    for font_dir in font_dirs:
        if os.path.isdir(font_dir):
            for ext in ("*.ttf", "*.ttc", "*.otf"):
                for path in glob.glob(os.path.join(font_dir, "**", ext), recursive=True):
                    name_lower = os.path.basename(path).lower()
                    if any(kw in name_lower for kw in (
                        "noto", "cjk", "wqy", "hei", "song", "ming", 
                        "gothic", "ping", "msyh", "simsun", "simhei"
                    )):
                        if path not in font_search_paths:
                            font_search_paths.append(path)
    
    # Try each font path
    for font_path in font_search_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(CJK_FONT_NAME, font_path))
                pdfmetrics.registerFont(TTFont(f"{CJK_FONT_NAME}-Bold", font_path))
                addMapping(CJK_FONT_NAME, 0, 0, CJK_FONT_NAME)
                addMapping(CJK_FONT_NAME, 1, 0, f"{CJK_FONT_NAME}-Bold")
                addMapping(CJK_FONT_NAME, 0, 1, CJK_FONT_NAME)
                addMapping(CJK_FONT_NAME, 1, 1, f"{CJK_FONT_NAME}-Bold")
                print(f"CJK font registered: {font_path}")
                _fonts_registered = True
                return True
            except Exception as e:
                print(f"Failed to register font {font_path}: {e}")
                continue
    
    # Fallback: use reportlab built-in CID font
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        CJK_FONT_NAME = "STSong-Light"
        print("Registered fallback CID font: STSong-Light")
        _fonts_registered = True
        return True
    except Exception:
        pass
    
    print("WARNING: No CJK fonts found. Chinese text may not render correctly.")
    return False


def get_cjk_styles():
    """Get reportlab styles with CJK font applied to all text styles.
    
    Returns:
        StyleSheet with CJK font applied to all standard styles.
    """
    if not _fonts_registered:
        register_cjk_fonts()
    
    styles = getSampleStyleSheet()
    
    # Override all standard styles with CJK font
    for style_name in [
        'Normal', 'BodyText', 'Italic', 'Title', 
        'Heading1', 'Heading2', 'Heading3', 'Heading4', 'Heading5', 'Heading6',
        'Bullet', 'Definition', 'Code', 'UnorderedList', 'OrderedList'
    ]:
        if style_name in styles:
            styles[style_name].fontName = CJK_FONT_NAME
    
    return styles


if __name__ == "__main__":
    # Test CJK font registration
    success = register_cjk_fonts()
    if success:
        print(f"✓ CJK font registered successfully as '{CJK_FONT_NAME}'")
        
        # Test creating a simple PDF with Chinese text
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        
        styles = get_cjk_styles()
        
        test_path = "cjk_test.pdf"
        doc = SimpleDocTemplate(test_path, pagesize=A4)
        story = [
            Paragraph("中文测试标题", styles['Title']),
            Spacer(1, 12),
            Paragraph("这是一段中文正文内容，用于测试 CJK 字体是否正确注册。", styles['Normal']),
            Spacer(1, 12),
            Paragraph("English text should also work correctly.", styles['Normal']),
        ]
        doc.build(story)
        print(f"✓ Test PDF created: {test_path}")
    else:
        print("✗ Failed to register CJK font")

