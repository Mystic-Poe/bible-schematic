#!/usr/bin/env python3
"""
Add missing chapters to Bible of Insight vault
"""

import sqlite3
from pathlib import Path

DB_FILE = "bible.db"
VAULT_DIR = Path("Bible of Insight")

# Missing chapters
MISSING_CHAPTERS = [
    ("Daniel", 12),
    ("Nahum", 3),
    ("1 Timothy", 6),
]

def sanitize_filename(name):
    """Make name safe for filesystem"""
    return name.replace(" ", "_").replace("/", "_")

def load_all_cross_references(conn):
    """Pre-load all cross-references into memory"""
    print("Loading cross-references into memory...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT from_book, from_chapter, from_verse,
               to_book, to_chapter, to_verse, votes
        FROM verse_cross_references
        ORDER BY from_book, from_chapter, from_verse, votes DESC
    """)

    xrefs = {}
    for row in cursor.fetchall():
        key = (row[0], row[1], row[2])
        if key not in xrefs:
            xrefs[key] = []
        if len(xrefs[key]) < 10:
            xrefs[key].append((row[3], row[4], row[5], row[6]))

    print(f"  Loaded cross-references for {len(xrefs)} verses")
    return xrefs

def format_verse_link(book_name, chapter, verse):
    """Format as Obsidian WikiLink"""
    folder = sanitize_filename(book_name)
    file = f"Chapter_{chapter}"
    display = f"{book_name} {chapter}:{verse}"
    return f"[[{folder}/{file}#Verse {verse}|{display}]]"

def create_chapter_file(conn, xrefs_cache, book_name, chapter_num):
    """Create markdown file for a single chapter"""
    cursor = conn.cursor()

    # Get verses for this chapter
    cursor.execute("""
        SELECT v.verse, v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        WHERE b.book_name = ? AND v.chapter = ?
        ORDER BY v.verse
    """, (book_name, chapter_num))

    verses = cursor.fetchall()

    if not verses:
        print(f"  ⚠️  No verses found for {book_name} {chapter_num}")
        return None

    # Build markdown content
    lines = [
        f"# {book_name} Chapter {chapter_num}",
        "",
        f"**{len(verses)} verses**",
        "",
        "---",
        ""
    ]

    for verse_num, text in verses:
        # Verse header
        lines.append(f"## Verse {verse_num}")
        lines.append("")
        lines.append(f"> {text}")
        lines.append("")

        # Cross-references
        key = (book_name, chapter_num, verse_num)
        verse_xrefs = xrefs_cache.get(key, [])

        if verse_xrefs:
            lines.append("**Cross-references:**")
            for to_book, to_chapter, to_verse, votes in verse_xrefs:
                link = format_verse_link(to_book, to_chapter, to_verse)
                lines.append(f"- {link} (votes: {votes})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)

def main():
    """Generate missing chapter files"""
    print("="*60)
    print("Adding Missing Chapters to Bible of Insight")
    print("="*60 + "\n")

    conn = sqlite3.connect(DB_FILE)

    # Pre-load cross-references
    xrefs_cache = load_all_cross_references(conn)

    print("\nGenerating missing chapters:")
    print("="*60)

    for book_name, chapter_num in MISSING_CHAPTERS:
        print(f"\n{book_name} Chapter {chapter_num}:")
        print("-"*60)

        # Create folder if needed
        folder_name = sanitize_filename(book_name)
        folder_path = VAULT_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        # Create chapter file
        content = create_chapter_file(conn, xrefs_cache, book_name, chapter_num)

        if content:
            file_path = folder_path / f"Chapter_{chapter_num}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Count verses
            verse_count = content.count("## Verse ")
            print(f"  ✓ Created: {file_path}")
            print(f"  Verses: {verse_count}")
        else:
            print(f"  ❌ Failed to create chapter")

    conn.close()

    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    print("Missing chapters have been added to Bible of Insight vault")
    print("\nFiles created:")
    for book_name, chapter_num in MISSING_CHAPTERS:
        folder = sanitize_filename(book_name)
        print(f"  - {folder}/Chapter_{chapter_num}.md")
    print("="*60)

if __name__ == "__main__":
    main()
