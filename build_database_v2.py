#!/usr/bin/env python3
"""
Build SQLite database from Bible PDFs - Version 2
Uses smarter verse parsing with expected chapter/verse counts
"""

import os
import re
import sqlite3
from pypdf import PdfReader
from pathlib import Path

# Database file
DB_FILE = "bible.db"

# Book metadata with chapter counts
# (book_number, name, testament, chapter_count)
BOOKS = [
    (1, "Genesis", "Old", 50), (2, "Exodus", "Old", 40), (3, "Leviticus", "Old", 27),
    (4, "Numbers", "Old", 36), (5, "Deuteronomy", "Old", 34), (6, "Joshua", "Old", 24),
    (7, "Judges", "Old", 21), (8, "Ruth", "Old", 4), (9, "1 Samuel", "Old", 31),
    (10, "2 Samuel", "Old", 24), (11, "1 Kings", "Old", 22), (12, "2 Kings", "Old", 25),
    (13, "1 Chronicles", "Old", 29), (14, "2 Chronicles", "Old", 36), (15, "Ezra", "Old", 10),
    (16, "Nehemiah", "Old", 13), (17, "Esther", "Old", 10), (18, "Job", "Old", 42),
    (19, "Psalms", "Old", 150), (20, "Proverbs", "Old", 31), (21, "Ecclesiastes", "Old", 12),
    (22, "Song of Solomon", "Old", 8), (23, "Isaiah", "Old", 66), (24, "Jeremiah", "Old", 52),
    (25, "Lamentations", "Old", 5), (26, "Ezekiel", "Old", 48), (27, "Daniel", "Old", 12),
    (28, "Hosea", "Old", 14), (29, "Joel", "Old", 3), (30, "Amos", "Old", 9),
    (31, "Obadiah", "Old", 1), (32, "Jonah", "Old", 4), (33, "Micah", "Old", 7),
    (34, "Nahum", "Old", 3), (35, "Habakkuk", "Old", 3), (36, "Zephaniah", "Old", 3),
    (37, "Haggai", "Old", 2), (38, "Zechariah", "Old", 14), (39, "Malachi", "Old", 4),
    (40, "Matthew", "New", 28), (41, "Mark", "New", 16), (42, "Luke", "New", 24),
    (43, "John", "New", 21), (44, "Acts", "New", 28), (45, "Romans", "New", 16),
    (46, "1 Corinthians", "New", 16), (47, "2 Corinthians", "New", 13),
    (48, "Galatians", "New", 6), (49, "Ephesians", "New", 6), (50, "Philippians", "New", 4),
    (51, "Colossians", "New", 4), (52, "1 Thessalonians", "New", 5),
    (53, "2 Thessalonians", "New", 3), (54, "1 Timothy", "New", 6),
    (55, "2 Timothy", "New", 4), (56, "Titus", "New", 3), (57, "Philemon", "New", 1),
    (58, "Hebrews", "New", 13), (59, "James", "New", 5), (60, "1 Peter", "New", 5),
    (61, "2 Peter", "New", 3), (62, "1 John", "New", 5), (63, "2 John", "New", 1),
    (64, "3 John", "New", 1), (65, "Jude", "New", 1), (66, "Revelation", "New", 22)
]

def create_database():
    """Create database and tables from schema"""
    # Remove old database if exists
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    print("Creating database...")
    conn = sqlite3.connect(DB_FILE)

    # Read and execute schema
    with open('schema.sql', 'r') as f:
        schema = f.read()
    conn.executescript(schema)

    # Insert book metadata
    conn.executemany(
        "INSERT INTO books (book_id, book_number, book_name, testament) VALUES (?, ?, ?, ?)",
        [(i, num, name, test) for i, (num, name, test, _) in enumerate(BOOKS, 1)]
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

def parse_verses_smart(text, book_name, expected_chapters):
    """
    Smart verse parsing using expected chapter count
    Returns list of tuples: (chapter, verse, text)
    """
    verses = []

    # Remove the book title from the beginning
    text = re.sub(rf'^{re.escape(book_name)}\s*\n*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = text.strip()

    # Split by verse numbers (digit followed by capital letter or quote)
    # Pattern: number at word boundary followed by uppercase or quote
    verse_pattern = re.compile(r'(?:^|\n)(\d+)([A-Z"\'].*?)(?=(?:^|\n)\d+[A-Z"\']|$)', re.MULTILINE | re.DOTALL)

    matches = list(verse_pattern.finditer(text))

    if not matches:
        # Fallback: simpler pattern
        verse_pattern = re.compile(r'(\d+)([A-Z].*?)(?=\d+[A-Z]|$)', re.DOTALL)
        matches = list(verse_pattern.finditer(text))

    if not matches:
        print(f"  Warning: No verses found in {book_name}")
        return verses

    current_chapter = 1
    prev_verse_num = 0
    verses_in_chapter = 0

    for i, match in enumerate(matches):
        verse_num = int(match.group(1))
        verse_text = match.group(2).strip()

        # Clean up verse text
        verse_text = re.sub(r'\s+', ' ', verse_text).strip()

        # Skip if empty
        if not verse_text or len(verse_text) < 3:
            continue

        # Chapter change detection:
        # If verse number drops significantly (like 50->1 or even 10->1)
        # AND we haven't exceeded our expected chapter count
        if verse_num == 1 and prev_verse_num > 3 and current_chapter < expected_chapters:
            current_chapter += 1
            verses_in_chapter = 0

        # Only add if not a duplicate and seems valid
        if verse_num > 0:
            verses.append((current_chapter, verse_num, verse_text))
            verses_in_chapter += 1

        prev_verse_num = verse_num

    return verses

def process_book(conn, book_id, book_number, book_name, chapter_count):
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
    verses = parse_verses_smart(text, book_name, chapter_count)

    if not verses:
        return 0

    # Insert verses into database
    cursor = conn.cursor()
    inserted = 0
    for chapter, verse, text in verses:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO verses (book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                (book_id, chapter, verse, text)
            )
            if cursor.rowcount > 0:
                inserted += 1
        except sqlite3.Error as e:
            print(f"  Error inserting {book_name} {chapter}:{verse}: {e}")

    conn.commit()

    # Verify chapter count
    cursor.execute("SELECT COUNT(DISTINCT chapter) FROM verses WHERE book_id = ?", (book_id,))
    actual_chapters = cursor.fetchone()[0]

    print(f"  Inserted {inserted} verses across {actual_chapters}/{chapter_count} chapters")
    return inserted

def main():
    """Main execution"""
    print("="*60)
    print("Bible Database Builder v2")
    print("="*60)

    # Create database
    conn = create_database()

    # Process each book
    total_verses = 0
    for book_id, (book_number, book_name, testament, chapter_count) in enumerate(BOOKS, 1):
        verse_count = process_book(conn, book_id, book_number, book_name, chapter_count)
        total_verses += verse_count

    # Summary
    print("="*60)
    print(f"Database build complete!")

    # Detailed stats
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
