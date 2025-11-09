# Bible Schematic - NKJV SQL Database

A comprehensive SQLite database containing the complete New King James Version (NKJV) Bible with verse-level granularity and cross-references.

## Database Contents

- **66 Books** (39 Old Testament + 27 New Testament)
- **30,642 Verses** (complete NKJV text)
- **418,734 Cross-References** (from Treasury of Scripture Knowledge)

## Database Schema

### Tables

#### `books`
Metadata about each book of the Bible
- `book_id` - Unique identifier
- `book_number` - Canonical ordering (1-66)
- `book_name` - Book name (e.g., "Genesis", "John")
- `testament` - "Old" or "New"

#### `verses`
Individual verses with full text
- `verse_id` - Unique identifier
- `book_id` - Foreign key to books table
- `chapter` - Chapter number
- `verse` - Verse number
- `text` - Full verse text (NKJV)

#### `cross_references`
Links between related verses
- `xref_id` - Unique identifier
- `from_verse_id` - Source verse
- `to_verse_id` - Related verse
- `votes` - Popularity/relevance score

### Views

#### `bible_verses`
Easy verse lookup with book names
```sql
SELECT book_name, chapter, verse, text
FROM bible_verses
WHERE book_name = 'John' AND chapter = 3 AND verse = 16;
```

#### `verse_cross_references`
Human-readable cross-references
```sql
SELECT * FROM verse_cross_references
WHERE from_book = 'Genesis' AND from_chapter = 1 AND from_verse = 1;
```

## Files

### Database
- `bible.db` - SQLite database file (16MB)

### Schema
- `schema.sql` - Database schema definition

### Scripts

#### Data Population
- `fetch_nkjv_api.py` - Fetches NKJV text from Bolls.life API
- `import_cross_references.py` - Imports cross-references from SQL files

#### Testing
- `test_queries.py` - Example queries demonstrating database usage

#### Development/Legacy
- `build_database.py` - PDF extraction attempt (legacy)
- `build_database_v2.py` - Improved PDF parser (legacy)
- `test_pdf_structure.py` - PDF analysis tool (legacy)
- `debug_parse.py` - Debug script (legacy)

### PDF Source Files
Individual books as PDF files (66 files):
- `01_Genesis.pdf` through `66_Revelation.pdf`
- `split_log.txt` - Log from PDF splitting process

## Usage Examples

### Python

```python
import sqlite3

conn = sqlite3.connect('bible.db')
cursor = conn.cursor()

# Get a specific verse
cursor.execute("""
    SELECT text FROM bible_verses
    WHERE book_name = 'John' AND chapter = 3 AND verse = 16
""")
print(cursor.fetchone()[0])

# Search for verses
cursor.execute("""
    SELECT book_name, chapter, verse, text
    FROM bible_verses
    WHERE text LIKE '%love%'
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"{row[0]} {row[1]}:{row[2]} - {row[3][:50]}...")

# Get cross-references
cursor.execute("""
    SELECT to_book, to_chapter, to_verse
    FROM verse_cross_references
    WHERE from_book = 'Genesis' AND from_chapter = 1 AND from_verse = 1
    ORDER BY votes DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"{row[0]} {row[1]}:{row[2]}")

conn.close()
```

### Command Line

```bash
# Run test queries
python test_queries.py

# Query directly with Python
python3 -c "import sqlite3; conn = sqlite3.connect('bible.db'); \
cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM verses'); \
print(f'Total verses: {cursor.fetchone()[0]}')"
```

## Data Sources

- **NKJV Text**: [Bolls.life API](https://bolls.life/api/)
- **Cross-References**: [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
- **Original PDFs**: Split from complete NKJV Bible PDF

## Rebuild Instructions

To rebuild the database from scratch:

1. **Fetch NKJV verses** (requires internet):
   ```bash
   python fetch_nkjv_api.py
   ```
   This will create `bible.db` with all verses (takes ~10-15 minutes)

2. **Import cross-references**:
   ```bash
   python import_cross_references.py
   ```
   This adds cross-references to the database (takes ~10-15 minutes)

3. **Test the database**:
   ```bash
   python test_queries.py
   ```

## License & Copyright

- **NKJV Text**: Copyright © Thomas Nelson, Inc. The NKJV text is copyrighted. This database is for personal study use.
- **Cross-Reference Data**: Public domain (Treasury of Scripture Knowledge)
- **Database Schema & Scripts**: MIT License

## Statistics

- **Old Testament**: 22,753 verses across 39 books
- **New Testament**: 7,889 verses across 27 books
- **Longest Book**: Psalms (2,448 verses)
- **Total Size**: ~16MB (SQLite database)

## Notes

- Some chapters may be missing due to API timeouts during fetch (~12,800 cross-references couldn't be mapped due to missing verses)
- The database uses UTF-8 encoding
- All book names use standard English names (e.g., "1 Samuel", "2 Corinthians")
- Verse IDs are auto-incrementing and stable

---

**Generated with [Claude Code](https://claude.com/claude-code)**
