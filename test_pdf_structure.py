#!/usr/bin/env python3
"""Quick test to see how the PDF text is structured"""

from pypdf import PdfReader

# Test with Genesis
pdf_path = "01_Genesis.pdf"
reader = PdfReader(pdf_path)

print(f"Total pages: {len(reader.pages)}")
print("\n" + "="*60)
print("FIRST PAGE TEXT:")
print("="*60)
print(reader.pages[0].extract_text())
print("\n" + "="*60)
print("SECOND PAGE TEXT:")
print("="*60)
print(reader.pages[1].extract_text())
