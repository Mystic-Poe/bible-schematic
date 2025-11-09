#!/usr/bin/env python3
"""Debug PDF parsing"""

from pypdf import PdfReader

# Check a book that failed
pdf = PdfReader("46_1_Corinthians.pdf")
print("=== 1 Corinthians - First Page ===")
print(pdf.pages[0].extract_text()[:1000])
print("\n=== Second Page ===")
print(pdf.pages[1].extract_text()[:500])
