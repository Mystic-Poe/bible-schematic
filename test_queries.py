#!/usr/bin/env python3
"""
Test queries to demonstrate the Bible database
"""

import sqlite3

DB_FILE = "bible.db"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(title)
    print("="*60)

def test_verse_lookup():
    """Test looking up a specific verse"""
    print_section("Test 1: Verse Lookup - John 3:16")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT book_name, chapter, verse, text
        FROM bible_verses
        WHERE book_name = 'John' AND chapter = 3 AND verse = 16
    """)

    result = cursor.fetchone()
    if result:
        print(f"\n{result[0]} {result[1]}:{result[2]}")
        print(f"{result[3]}")
    conn.close()

def test_chapter_lookup():
    """Test getting all verses from a chapter"""
    print_section("Test 2: Chapter Lookup - Psalm 23 (first 3 verses)")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT verse, text
        FROM bible_verses
        WHERE book_name = 'Psalms' AND chapter = 23
        LIMIT 3
    """)

    for row in cursor.fetchall():
        print(f"\n{row[0]}. {row[1]}")
    conn.close()

def test_cross_references():
    """Test finding cross-references for a verse"""
    print_section("Test 3: Cross-References for Genesis 1:1")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            to_book, to_chapter, to_verse, votes
        FROM verse_cross_references
        WHERE from_book = 'Genesis' AND from_chapter = 1 AND from_verse = 1
        ORDER BY votes DESC
        LIMIT 5
    """)

    print("\nTop 5 cross-references:")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]}:{row[2]} (votes: {row[3]})")
    conn.close()

def test_search():
    """Test searching for verses containing specific text"""
    print_section("Test 4: Search - 'love one another'")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT book_name, chapter, verse, text
        FROM bible_verses
        WHERE text LIKE '%love one another%'
        LIMIT 3
    """)

    for row in cursor.fetchall():
        print(f"\n{row[0]} {row[1]}:{row[2]}")
        print(f"{row[3]}")
    conn.close()

def test_statistics():
    """Show database statistics"""
    print_section("Test 5: Database Statistics")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Books
    cursor.execute("SELECT COUNT(*) FROM books")
    print(f"\nTotal books: {cursor.fetchone()[0]}")

    # Verses
    cursor.execute("SELECT COUNT(*) FROM verses")
    print(f"Total verses: {cursor.fetchone()[0]}")

    # Cross-references
    cursor.execute("SELECT COUNT(*) FROM cross_references")
    print(f"Total cross-references: {cursor.fetchone()[0]}")

    # Verses per testament
    cursor.execute("""
        SELECT b.testament, COUNT(v.verse_id)
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        GROUP BY b.testament
    """)
    print("\nVerses by testament:")
    for row in cursor.fetchall():
        print(f"  {row[0]} Testament: {row[1]} verses")

    # Longest book
    cursor.execute("""
        SELECT b.book_name, COUNT(v.verse_id) as verse_count
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        GROUP BY b.book_name
        ORDER BY verse_count DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    print(f"\nLongest book: {result[0]} ({result[1]} verses)")

    conn.close()

def main():
    """Run all test queries"""
    print("="*60)
    print("Bible Database Query Tests")
    print("="*60)

    test_verse_lookup()
    test_chapter_lookup()
    test_cross_references()
    test_search()
    test_statistics()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
