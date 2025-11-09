#!/usr/bin/env python3
"""
Fetch NKJV Bible from Bolls.life API and populate SQLite database
"""

import sqlite3
import requests
import time
import json
from pathlib import Path

# Database file
DB_FILE = "bible.db"
API_BASE = "https://bolls.life/get-chapter/NKJV"

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
    if Path(DB_FILE).exists():
        Path(DB_FILE).unlink()

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
    print(f"Created database with {len(BOOKS)} books\n")
    return conn

def fetch_chapter(book_num, chapter_num):
    """Fetch a chapter from Bolls API"""
    url = f"{API_BASE}/{book_num}/{chapter_num}/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching chapter: {e}")
        return None

def process_book(conn, book_id, book_number, book_name, chapter_count):
    """Fetch all chapters for a book and insert verses"""
    print(f"Fetching {book_name} ({chapter_count} chapters)...")

    cursor = conn.cursor()
    total_verses = 0

    for chapter in range(1, chapter_count + 1):
        # Fetch chapter data
        data = fetch_chapter(book_number, chapter)

        if not data:
            print(f"  Warning: Failed to fetch chapter {chapter}")
            continue

        # Parse verses - API returns list of verse objects
        # Expected format: [{"verse": 1, "text": "..."}, ...]
        if isinstance(data, list):
            for verse_data in data:
                verse_num = verse_data.get('verse', 0)
                verse_text = verse_data.get('text', '').strip()

                if verse_num and verse_text:
                    try:
                        cursor.execute(
                            "INSERT OR IGNORE INTO verses (book_id, chapter, verse, text) VALUES (?, ?, ?, ?)",
                            (book_id, chapter, verse_num, verse_text)
                        )
                        if cursor.rowcount > 0:
                            total_verses += 1
                    except sqlite3.Error as e:
                        print(f"  Error inserting {book_name} {chapter}:{verse_num}: {e}")

        # Small delay to be respectful to the API
        time.sleep(0.1)

    conn.commit()
    print(f"  ✓ Inserted {total_verses} verses")
    return total_verses

def main():
    """Main execution"""
    print("="*60)
    print("NKJV Bible Database Builder - Bolls API")
    print("="*60 + "\n")

    # Create database
    conn = create_database()

    # Process each book
    total_verses = 0
    for book_id, (book_number, book_name, testament, chapter_count) in enumerate(BOOKS, 1):
        verse_count = process_book(conn, book_id, book_number, book_name, chapter_count)
        total_verses += verse_count

    # Summary
    print("\n" + "="*60)
    print("Database build complete!")

    # Stats
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
