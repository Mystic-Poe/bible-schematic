#!/usr/bin/env python3
"""
Verify Bible database completeness
"""

import sqlite3

DB_FILE = "bible.db"

# Expected Bible structure
EXPECTED_BOOKS = [
    ('Genesis', 'Old', 50),
    ('Exodus', 'Old', 40),
    ('Leviticus', 'Old', 27),
    ('Numbers', 'Old', 36),
    ('Deuteronomy', 'Old', 34),
    ('Joshua', 'Old', 24),
    ('Judges', 'Old', 21),
    ('Ruth', 'Old', 4),
    ('1 Samuel', 'Old', 31),
    ('2 Samuel', 'Old', 24),
    ('1 Kings', 'Old', 22),
    ('2 Kings', 'Old', 25),
    ('1 Chronicles', 'Old', 29),
    ('2 Chronicles', 'Old', 36),
    ('Ezra', 'Old', 10),
    ('Nehemiah', 'Old', 13),
    ('Esther', 'Old', 10),
    ('Job', 'Old', 42),
    ('Psalms', 'Old', 150),
    ('Proverbs', 'Old', 31),
    ('Ecclesiastes', 'Old', 12),
    ('Song of Solomon', 'Old', 8),
    ('Isaiah', 'Old', 66),
    ('Jeremiah', 'Old', 52),
    ('Lamentations', 'Old', 5),
    ('Ezekiel', 'Old', 48),
    ('Daniel', 'Old', 12),
    ('Hosea', 'Old', 14),
    ('Joel', 'Old', 3),
    ('Amos', 'Old', 9),
    ('Obadiah', 'Old', 1),
    ('Jonah', 'Old', 4),
    ('Micah', 'Old', 7),
    ('Nahum', 'Old', 3),
    ('Habakkuk', 'Old', 3),
    ('Zephaniah', 'Old', 3),
    ('Haggai', 'Old', 2),
    ('Zechariah', 'Old', 14),
    ('Malachi', 'Old', 4),
    ('Matthew', 'New', 28),
    ('Mark', 'New', 16),
    ('Luke', 'New', 24),
    ('John', 'New', 21),
    ('Acts', 'New', 28),
    ('Romans', 'New', 16),
    ('1 Corinthians', 'New', 16),
    ('2 Corinthians', 'New', 13),
    ('Galatians', 'New', 6),
    ('Ephesians', 'New', 6),
    ('Philippians', 'New', 4),
    ('Colossians', 'New', 4),
    ('1 Thessalonians', 'New', 5),
    ('2 Thessalonians', 'New', 3),
    ('1 Timothy', 'New', 6),
    ('2 Timothy', 'New', 4),
    ('Titus', 'New', 3),
    ('Philemon', 'New', 1),
    ('Hebrews', 'New', 13),
    ('James', 'New', 5),
    ('1 Peter', 'New', 5),
    ('2 Peter', 'New', 3),
    ('1 John', 'New', 5),
    ('2 John', 'New', 1),
    ('3 John', 'New', 1),
    ('Jude', 'New', 1),
    ('Revelation', 'New', 22),
]

def verify_database():
    """Verify database completeness"""
    print("="*60)
    print("Bible Database Verification")
    print("="*60 + "\n")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check overall counts
    print("Overall Statistics:")
    print("-"*60)

    cursor.execute("SELECT COUNT(*) FROM books")
    book_count = cursor.fetchone()[0]
    print(f"Books in database: {book_count}/66")

    cursor.execute("SELECT COUNT(*) FROM verses")
    verse_count = cursor.fetchone()[0]
    print(f"Total verses: {verse_count:,} (expected ~31,102)")

    cursor.execute("SELECT COUNT(*) FROM cross_references")
    xref_count = cursor.fetchone()[0]
    print(f"Cross-references: {xref_count:,}")

    # Check each book
    print("\n" + "="*60)
    print("Book-by-Book Verification:")
    print("="*60)

    cursor.execute("""
        SELECT book_name, testament, MAX(chapter) as max_chapter
        FROM books b
        JOIN verses v ON b.book_id = v.book_id
        GROUP BY book_name, testament
        ORDER BY b.book_number
    """)

    actual_books = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    missing_books = []
    incorrect_chapters = []

    for book_name, expected_testament, expected_chapters in EXPECTED_BOOKS:
        if book_name not in actual_books:
            missing_books.append(book_name)
            print(f"❌ {book_name}: MISSING")
        else:
            actual_testament, actual_chapters = actual_books[book_name]
            if actual_chapters == expected_chapters:
                print(f"✓ {book_name}: {actual_chapters} chapters")
            else:
                incorrect_chapters.append((book_name, actual_chapters, expected_chapters))
                print(f"⚠️  {book_name}: {actual_chapters}/{expected_chapters} chapters")

    # Check for gaps in verses
    print("\n" + "="*60)
    print("Checking for gaps in verse numbering:")
    print("="*60)

    cursor.execute("""
        SELECT b.book_name, v.chapter, COUNT(*) as verse_count
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        GROUP BY b.book_name, v.chapter
        HAVING verse_count = 0
    """)

    gaps = cursor.fetchall()
    if gaps:
        print(f"Found {len(gaps)} chapters with no verses:")
        for book, chapter, count in gaps[:10]:
            print(f"  {book} {chapter}")
    else:
        print("No obvious gaps found")

    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)

    if missing_books:
        print(f"\n❌ Missing {len(missing_books)} books:")
        for book in missing_books:
            print(f"   - {book}")

    if incorrect_chapters:
        print(f"\n⚠️  {len(incorrect_chapters)} books with incorrect chapter counts:")
        for book, actual, expected in incorrect_chapters:
            print(f"   - {book}: has {actual}, expected {expected}")

    if not missing_books and not incorrect_chapters:
        print("\n✓ Database appears complete!")
        print(f"  - All 66 books present")
        print(f"  - {verse_count:,} verses loaded")
        print(f"  - {xref_count:,} cross-references")

    conn.close()

if __name__ == "__main__":
    verify_database()
