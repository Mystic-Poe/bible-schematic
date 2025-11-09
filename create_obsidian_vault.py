#!/usr/bin/env python3
"""
Create Obsidian vault with hyperlinked cross-references
Generates markdown files organized by book/chapter with WikiLink cross-references
"""

import sqlite3
import os
from pathlib import Path

DB_FILE = "bible.db"
VAULT_NAME = "Bible of Insight"

def create_vault_structure():
    """Create the vault directory structure"""
    vault_path = Path(VAULT_NAME)
    if vault_path.exists():
        print(f"Warning: {VAULT_NAME} already exists. Recreating...")
        import shutil
        shutil.rmtree(vault_path)

    vault_path.mkdir(exist_ok=True)
    print(f"Created vault: {VAULT_NAME}/")
    return vault_path

def sanitize_filename(name):
    """Sanitize book name for use as folder name"""
    # Replace spaces and special characters
    return name.replace(" ", "_").replace(":", "").replace("/", "_")

def format_verse_link(book_name, chapter, verse):
    """Format a cross-reference as an Obsidian WikiLink"""
    # Obsidian link format: [[Book_Name/Chapter_X|Book Chapter:Verse]]
    folder = sanitize_filename(book_name)
    file = f"Chapter_{chapter}"
    display = f"{book_name} {chapter}:{verse}"

    # Link to the chapter file with anchor to specific verse
    return f"[[{folder}/{file}#Verse {verse}|{display}]]"

def load_all_cross_references(conn):
    """Pre-load all cross-references into memory for fast lookup"""
    print("Loading cross-references into memory...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT from_book, from_chapter, from_verse,
               to_book, to_chapter, to_verse, votes
        FROM verse_cross_references
        ORDER BY from_book, from_chapter, from_verse, votes DESC
    """)

    # Build dictionary: {(book, chapter, verse): [(to_book, to_chapter, to_verse, votes), ...]}
    xrefs = {}
    for row in cursor.fetchall():
        key = (row[0], row[1], row[2])
        if key not in xrefs:
            xrefs[key] = []
        if len(xrefs[key]) < 10:  # Limit to top 10 per verse
            xrefs[key].append((row[3], row[4], row[5], row[6]))

    print(f"Loaded {len(xrefs)} verses with cross-references")
    return xrefs

def get_cross_references(xrefs_cache, book_name, chapter, verse):
    """Get cross-references for a specific verse from cache"""
    key = (book_name, chapter, verse)
    return xrefs_cache.get(key, [])

def create_chapter_markdown(conn, vault_path, book_name, book_number, chapter_num, testament, xrefs_cache):
    """Create a markdown file for a chapter with cross-references"""

    # Get all verses for this chapter
    cursor = conn.cursor()
    cursor.execute("""
        SELECT verse, text
        FROM bible_verses
        WHERE book_name = ? AND chapter = ?
        ORDER BY verse
    """, (book_name, chapter_num))

    verses = cursor.fetchall()

    if not verses:
        return 0

    # Create book folder
    book_folder = vault_path / sanitize_filename(book_name)
    book_folder.mkdir(exist_ok=True)

    # Create chapter file
    chapter_file = book_folder / f"Chapter_{chapter_num}.md"

    with open(chapter_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"# {book_name} {chapter_num}\n\n")
        f.write(f"*{testament} Testament, Book {book_number}*\n\n")
        f.write("---\n\n")

        # Write verses with cross-references
        for verse_num, verse_text in verses:
            # Verse header with anchor
            f.write(f"## Verse {verse_num}\n\n")

            # Verse text
            f.write(f"> {verse_text}\n\n")

            # Get cross-references from cache
            xrefs = get_cross_references(xrefs_cache, book_name, chapter_num, verse_num)

            if xrefs:
                f.write(f"**Cross-References:**\n")
                for xref_book, xref_chapter, xref_verse, votes in xrefs:
                    link = format_verse_link(xref_book, xref_chapter, xref_verse)
                    f.write(f"- {link} *(votes: {votes})*\n")
                f.write("\n")

            f.write("---\n\n")

    return len(verses)

def create_book_index(vault_path, book_name, book_number, testament, chapters):
    """Create an index file for each book"""
    book_folder = vault_path / sanitize_filename(book_name)
    index_file = book_folder / "README.md"

    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(f"# {book_name}\n\n")
        f.write(f"**Testament:** {testament}\n")
        f.write(f"**Book Number:** {book_number}\n")
        f.write(f"**Chapters:** {len(chapters)}\n\n")
        f.write("## Chapters\n\n")

        for chapter in sorted(chapters):
            f.write(f"- [[{sanitize_filename(book_name)}/Chapter_{chapter}|Chapter {chapter}]]\n")

def create_vault_index(vault_path, conn):
    """Create main index file for the vault"""
    index_file = vault_path / "README.md"

    cursor = conn.cursor()

    # Get all books
    cursor.execute("""
        SELECT book_number, book_name, testament
        FROM books
        ORDER BY book_number
    """)

    books = cursor.fetchall()

    with open(index_file, 'w', encoding='utf-8') as f:
        f.write("# Bible of Insight\n\n")
        f.write("*Complete NKJV Bible with Hyperlinked Cross-References*\n\n")
        f.write("---\n\n")

        # Old Testament
        f.write("## Old Testament\n\n")
        for book_num, book_name, testament in books:
            if testament == "Old":
                folder = sanitize_filename(book_name)
                f.write(f"{book_num}. [[{folder}/README|{book_name}]]\n")

        f.write("\n## New Testament\n\n")
        for book_num, book_name, testament in books:
            if testament == "New":
                folder = sanitize_filename(book_name)
                f.write(f"{book_num}. [[{folder}/README|{book_name}]]\n")

        f.write("\n---\n\n")
        f.write("## Statistics\n\n")

        cursor.execute("SELECT COUNT(*) FROM verses")
        verse_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cross_references")
        xref_count = cursor.fetchone()[0]

        f.write(f"- **Total Books:** {len(books)}\n")
        f.write(f"- **Total Verses:** {verse_count:,}\n")
        f.write(f"- **Cross-References:** {xref_count:,}\n\n")

        f.write("---\n\n")
        f.write("*Generated from NKJV Bible Database*\n")

def main():
    """Main execution"""
    print("="*60)
    print("Obsidian Vault Generator - Bible of Insight")
    print("="*60 + "\n")

    # Connect to database
    if not Path(DB_FILE).exists():
        print(f"Error: Database file '{DB_FILE}' not found!")
        return

    conn = sqlite3.connect(DB_FILE)

    # Create vault structure
    vault_path = create_vault_structure()

    # Load all cross-references into memory (OPTIMIZATION!)
    xrefs_cache = load_all_cross_references(conn)

    # Get all books
    cursor = conn.cursor()
    cursor.execute("""
        SELECT book_number, book_name, testament
        FROM books
        ORDER BY book_number
    """)

    books = cursor.fetchall()

    total_verses = 0
    total_chapters = 0

    # Process each book
    for book_num, book_name, testament in books:
        print(f"Processing {book_name}...")

        # Get all chapters for this book
        cursor.execute("""
            SELECT DISTINCT chapter
            FROM verses
            WHERE book_id = (SELECT book_id FROM books WHERE book_name = ?)
            ORDER BY chapter
        """, (book_name,))

        chapters = [row[0] for row in cursor.fetchall()]

        # Create markdown for each chapter
        book_verse_count = 0
        for chapter in chapters:
            verse_count = create_chapter_markdown(
                conn, vault_path, book_name, book_num, chapter, testament, xrefs_cache
            )
            book_verse_count += verse_count

        # Create book index
        create_book_index(vault_path, book_name, book_num, testament, chapters)

        total_verses += book_verse_count
        total_chapters += len(chapters)

        print(f"  Created {len(chapters)} chapters with {book_verse_count} verses")

    # Create main vault index
    create_vault_index(vault_path, conn)

    conn.close()

    # Summary
    print("\n" + "="*60)
    print("Vault Creation Complete!")
    print("="*60)
    print(f"Location: {vault_path.absolute()}")
    print(f"Books: {len(books)}")
    print(f"Chapters: {total_chapters}")
    print(f"Verses: {total_verses:,}")
    print(f"\nTo use: Open '{VAULT_NAME}' as a vault in Obsidian")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
