#!/usr/bin/env python3
"""
Import cross-references from SQL files into the Bible database
"""

import sqlite3
import re
import glob
from pathlib import Path

DB_FILE = "bible.db"

def parse_sql_insert(line):
    """Parse an INSERT statement and extract values"""
    # Pattern: VALUES ('Genesis', 1, 1, 'Proverbs', 8, 22, 22, 59);
    pattern = r"VALUES\s*\('([^']+)',\s*(\d+),\s*(\d+),\s*'([^']+)',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)"
    match = re.search(pattern, line)
    if match:
        return {
            'from_book': match.group(1),
            'from_chapter': int(match.group(2)),
            'from_verse': int(match.group(3)),
            'to_book': match.group(4),
            'to_chapter': int(match.group(5)),
            'to_verse_start': int(match.group(6)),
            'to_verse_end': int(match.group(7)),
            'votes': int(match.group(8))
        }
    return None

def get_verse_id(conn, book_name, chapter, verse):
    """Look up verse_id by book name, chapter, and verse"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.verse_id
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name = ? AND v.chapter = ? AND v.verse = ?
    """, (book_name, chapter, verse))
    result = cursor.fetchone()
    return result[0] if result else None

def import_cross_references(conn):
    """Import cross-references from all SQL files"""
    print("Importing cross-references...")

    # Find all cross-reference SQL files
    sql_files = sorted(glob.glob("cross_references_*.sql"))

    if not sql_files:
        print("No cross-reference SQL files found!")
        return

    print(f"Found {len(sql_files)} cross-reference files")

    cursor = conn.cursor()
    total_imported = 0
    total_skipped = 0

    for sql_file in sql_files:
        print(f"Processing {sql_file}...")
        file_imported = 0
        lines_processed = 0

        with open(sql_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'VALUES' not in line:
                    continue

                lines_processed += 1
                data = parse_sql_insert(line)
                if not data:
                    if lines_processed <= 3:
                        print(f"  DEBUG: Failed to parse line: {line[:100]}")
                    continue

                # Look up verse IDs
                from_id = get_verse_id(conn, data['from_book'], data['from_chapter'], data['from_verse'])

                # Handle verse ranges in "to" reference
                # If to_verse_start == to_verse_end, it's a single verse
                # Otherwise, create cross-refs for the range
                if not from_id:
                    total_skipped += 1
                    continue

                for to_verse in range(data['to_verse_start'], data['to_verse_end'] + 1):
                    to_id = get_verse_id(conn, data['to_book'], data['to_chapter'], to_verse)

                    if not to_id:
                        total_skipped += 1
                        continue

                    # Insert cross-reference
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO cross_references
                            (from_verse_id, to_verse_id, votes)
                            VALUES (?, ?, ?)
                        """, (from_id, to_id, data['votes']))

                        if cursor.rowcount > 0:
                            file_imported += 1
                            total_imported += 1
                    except sqlite3.Error as e:
                        print(f"Error inserting cross-ref: {e}")

        conn.commit()
        print(f"  Processed {lines_processed} INSERT lines, imported {file_imported} cross-references")

    print(f"\nTotal cross-references imported: {total_imported}")
    print(f"Total skipped (verses not found): {total_skipped}")

def main():
    """Main execution"""
    print("="*60)
    print("Cross-Reference Import Tool")
    print("="*60 + "\n")

    if not Path(DB_FILE).exists():
        print(f"Error: Database file '{DB_FILE}' not found!")
        print("Please run fetch_nkjv_api.py first to create the database.")
        return

    conn = sqlite3.connect(DB_FILE)

    # Check if we have verses
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM verses")
    verse_count = cursor.fetchone()[0]

    if verse_count == 0:
        print("Error: No verses in database!")
        print("Please run fetch_nkjv_api.py first to populate verses.")
        conn.close()
        return

    print(f"Database has {verse_count} verses")

    # Import cross-references
    import_cross_references(conn)

    # Final stats
    cursor.execute("SELECT COUNT(*) FROM cross_references")
    xref_count = cursor.fetchone()[0]

    print("\n" + "="*60)
    print("Import complete!")
    print(f"Total cross-references in database: {xref_count}")
    print("="*60)

    conn.close()

if __name__ == "__main__":
    main()
