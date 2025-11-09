#!/usr/bin/env python3
"""
Fetch missing chapters from the NKJV Bible API
"""

import sqlite3
import requests
import time

DB_FILE = "bible.db"
API_BASE = "https://bolls.life/get-chapter/NKJV"

# Missing chapters: (book_name, book_number, chapter)
MISSING_CHAPTERS = [
    ("Daniel", 27, 12),
    ("Nahum", 34, 3),
    ("1 Timothy", 54, 6),
]

def get_book_id(conn, book_name):
    """Get book_id from database"""
    cursor = conn.cursor()
    cursor.execute("SELECT book_id FROM books WHERE book_name = ?", (book_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def fetch_chapter(book_num, chapter_num):
    """Fetch chapter from API"""
    url = f"{API_BASE}/{book_num}/{chapter_num}/"
    print(f"  Fetching from: {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error: {e}")
        return None

def insert_verses(conn, book_id, chapter_num, verses_data):
    """Insert verses into database"""
    cursor = conn.cursor()

    inserted = 0
    for verse_data in verses_data:
        verse_num = verse_data.get('verse')
        text = verse_data.get('text', '')

        if not text:
            continue

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO verses (book_id, chapter, verse, text)
                VALUES (?, ?, ?, ?)
            """, (book_id, chapter_num, verse_num, text))
            inserted += 1
        except Exception as e:
            print(f"    Error inserting verse {verse_num}: {e}")

    conn.commit()
    return inserted

def main():
    """Fetch missing chapters"""
    print("="*60)
    print("Fetching Missing Bible Chapters")
    print("="*60 + "\n")

    conn = sqlite3.connect(DB_FILE)

    total_verses = 0

    for book_name, book_num, chapter_num in MISSING_CHAPTERS:
        print(f"\n{book_name} Chapter {chapter_num}:")
        print("-"*60)

        # Get book_id
        book_id = get_book_id(conn, book_name)
        if not book_id:
            print(f"  ❌ Book not found in database: {book_name}")
            continue

        print(f"  Book ID: {book_id}")

        # Fetch chapter
        data = fetch_chapter(book_num, chapter_num)

        if not data:
            print(f"  ❌ Failed to fetch chapter")
            continue

        # Extract verses
        verses = data if isinstance(data, list) else []

        if not verses:
            print(f"  ❌ No verses found in response")
            continue

        print(f"  Retrieved {len(verses)} verses")

        # Insert verses
        inserted = insert_verses(conn, book_id, chapter_num, verses)
        total_verses += inserted

        print(f"  ✓ Inserted {inserted} verses")

        # Be nice to the API
        time.sleep(0.1)

    conn.close()

    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    print(f"Total verses inserted: {total_verses}")
    print("\nRun verify_database.py to confirm completeness")
    print("="*60)

if __name__ == "__main__":
    main()
