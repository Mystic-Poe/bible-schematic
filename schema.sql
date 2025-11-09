-- Bible Database Schema
-- NKJV Bible with Book/Chapter/Verse structure

-- Books table: metadata about each book
CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY,
    book_number INTEGER NOT NULL,
    book_name TEXT NOT NULL,
    testament TEXT NOT NULL CHECK(testament IN ('Old', 'New')),
    UNIQUE(book_number)
);

-- Verses table: individual verses with full reference
CREATE TABLE IF NOT EXISTS verses (
    verse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    UNIQUE(book_id, chapter, verse)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_verses_book_chapter ON verses(book_id, chapter);
CREATE INDEX IF NOT EXISTS idx_verses_book ON verses(book_id);

-- Cross-references table: links related verses
CREATE TABLE IF NOT EXISTS cross_references (
    xref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_verse_id INTEGER NOT NULL,
    to_verse_id INTEGER NOT NULL,
    votes INTEGER DEFAULT 0,
    FOREIGN KEY (from_verse_id) REFERENCES verses(verse_id),
    FOREIGN KEY (to_verse_id) REFERENCES verses(verse_id),
    UNIQUE(from_verse_id, to_verse_id)
);

-- Indexes for fast cross-reference lookups
CREATE INDEX IF NOT EXISTS idx_xref_from ON cross_references(from_verse_id);
CREATE INDEX IF NOT EXISTS idx_xref_to ON cross_references(to_verse_id);

-- View for easy querying with book names
CREATE VIEW IF NOT EXISTS bible_verses AS
SELECT
    b.book_name,
    b.testament,
    v.chapter,
    v.verse,
    v.text,
    b.book_number,
    v.verse_id
FROM verses v
JOIN books b ON v.book_id = b.book_id
ORDER BY b.book_number, v.chapter, v.verse;

-- View for cross-references with readable verse references
CREATE VIEW IF NOT EXISTS verse_cross_references AS
SELECT
    from_v.book_name AS from_book,
    from_v.chapter AS from_chapter,
    from_v.verse AS from_verse,
    to_v.book_name AS to_book,
    to_v.chapter AS to_chapter,
    to_v.verse AS to_verse,
    xr.votes
FROM cross_references xr
JOIN bible_verses from_v ON xr.from_verse_id = from_v.verse_id
JOIN bible_verses to_v ON xr.to_verse_id = to_v.verse_id;
