#!/usr/bin/env python3
"""
Build SQLite database from Bible PDFs
Extracts text from PDFs and parses into Book/Chapter/Verse structure
"""

import os
import re
import sqlite3
from pypdf import PdfReader
from pathlib import Path

# Database file
DB_FILE = "bible.db"

# Book metadata: (book_number, name, testament)
BOOKS = [
    (1, "Genesis", "Old"), (2, "Exodus", "Old"), (3, "Leviticus", "Old"),
    (4, "Numbers", "Old"), (5, "Deuteronomy", "Old"), (6, "Joshua", "Old"),
    (7, "Judges", "Old"), (8, "Ruth", "Old"), (9, "1 Samuel", "Old"),
    (10, "2 Samuel", "Old"), (11, "1 Kings", "Old"), (12, "2 Kings", "Old"),
    (13, "1 Chronicles", "Old"), (14, "2 Chronicles", "Old"), (15, "Ezra", "Old"),
    (16, "Nehemiah", "Old"), (17, "Esther", "Old"), (18, "Job", "Old"),
    (19, "Psalms", "Old"), (20, "Proverbs", "Old"), (21, "Ecclesiastes", "Old"),
    (22, "Song of Solomon", "Old"), (23, "Isaiah", "Old"), (24, "Jeremiah", "Old"),
    (25, "Lamentations", "Old"), (26, "Ezekiel", "Old"), (27, "Daniel", "Old"),
    (28, "Hosea", "Old"), (29, "Joel", "Old"), (30, "Amos", "Old"),
    (31, "Obadiah", "Old"), (32, "Jonah", "Old"), (33, "Micah", "Old"),
    (34, "Nahum", "Old"), (35, "Habakkuk", "Old"), (36, "Zephaniah", "Old"),
    (37, "Haggai", "Old"), (38, "Zechariah", "Old"), (39, "Malachi", "Old"),
    (40, "Matthew", "New"), (41, "Mark", "New"), (42, "Luke", "New"),
    (43, "John", "New"), (44, "Acts", "New"), (45, "Romans", "New"),
    (46, "1 Corinthians", "New"), (47, "2 Corinthians", "New"),
    (48, "Galatians", "New"), (49, "Ephesians", "New"), (50, "Philippians", "New"),
    (51, "Colossians", "New"), (52, "1 Thessalonians", "New"),
    (53, "2 Thessalonians", "New"), (54, "1 Timothy", "New"),
    (55, "2 Timothy", "New"), (56, "Titus", "New"), (57, "Philemon", "New"),
    (58, "Hebrews", "New"), (59, "James", "New"), (60, "1 Peter", "New"),
    (61, "2 Peter", "New"), (62, "1 John", "New"), (63, "2 John", "New"),
    (64, "3 John", "New"), (65, "Jude", "New"), (66, "Revelation", "New")
]

def create_database():
    """Create database and tables from schema"""
    print("Creating database...")
    conn = sqlite3.connect(DB_FILE)

    # Read and execute schema
    with open('schema.sql', 'r') as f:
        schema = f.read()
    conn.executescript(schema)

    # Insert book metadata
    conn.executemany(
        "INSERT INTO books (book_id, book_number, book_name, testament) VALUES (?, ?, ?, ?)",
        [(i, num, name, test) for i, (num, name, test) in enumerate(BOOKS, 1)]
    )
    conn.commit()
    print(f"Created database with {len(BOOKS)} books")
    return conn

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file"""
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

def parse_verses(text, book_name):
    """
    Parse text into chapter/verse structure
    Returns list of tuples: (chapter, verse, text)
    """
    verses = []
    current_chapter = 1

    # Remove the book title from the beginning
    text = re.sub(rf'^{re.escape(book_name)}\s*', '', text, flags=re.IGNORECASE)

    # Pattern to match verse numbers followed by text
    # Matches: "1Text here" or "1 Text here"
    verse_pattern = re.compile(r'(\d+)([A-Z].*?)(?=\d+[A-Z]|$)', re.DOTALL)

    matches = list(verse_pattern.finditer(text))

    if not matches:
        print(f"  Warning: No verses found in {book_name}")
        return verses

    prev_verse_num = 0

    for match in matches:
        verse_num = int(match.group(1))
        verse_text = match.group(2).strip()

        # Detect chapter change: if verse number is significantly lower than previous
        # (typically resets to 1 or 2 for new chapter)
        if verse_num <= 2 and prev_verse_num > 10:
            current_chapter += 1

        # Clean up the verse text
        verse_text = re.sub(r'\s+', ' ', verse_text).strip()

        if verse_text:
            verses.append((current_chapter, verse_num, verse_text))

        prev_verse_num = verse_num

    return verses

def process_book(conn, book_id, book_number, book_name):
    """Process a single book PDF and insert verses into database"""
    # Find the PDF file
    pdf_pattern = f"{str(book_number).zfill(2)}_*.pdf"
    pdf_files = list(Path('.').glob(pdf_pattern))

    if not pdf_files:
        print(f"  ERROR: No PDF found for {book_name}")
        return 0

    pdf_path = pdf_files[0]
    print(f"Processing {book_name} ({pdf_path})...")

    # Extract text
    text = extract_text_from_pdf(pdf_path)

    # Parse verses
    verses = parse_verses(text, book_name)

    if not verses:
        return 0

    # Insert verses into database
    cursor = conn.cursor()
    for chapter, verse, text in verses:
        try:
            cursor.execute(
                "INSERT INTO verses (book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                (book_id, chapter, verse, text)
            )
        except sqlite3.IntegrityError:
            print(f"  Warning: Duplicate verse {book_name} {chapter}:{verse}")

    conn.commit()
    print(f"  Inserted {len(verses)} verses")
    return len(verses)

def main():
    """Main execution"""
    print("="*60)
    print("Bible Database Builder")
    print("="*60)

    # Create database
    conn = create_database()

    # Process each book
    total_verses = 0
    for book_id, (book_number, book_name, testament) in enumerate(BOOKS, 1):
        verse_count = process_book(conn, book_id, book_number, book_name)
        total_verses += verse_count

    # Summary
    print("="*60)
    print(f"Database build complete!")
    print(f"Total verses inserted: {total_verses}")

    # Quick stats
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT book_id) FROM verses")
    book_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM verses")
    verse_count = cursor.fetchone()[0]

    print(f"Books in database: {book_count}/66")
    print(f"Total verses: {verse_count}")
    print(f"Database saved as: {DB_FILE}")
    print("="*60)

    conn.close()

if __name__ == "__main__":
    main()
