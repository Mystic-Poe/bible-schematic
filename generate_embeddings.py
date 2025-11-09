#!/usr/bin/env python3
"""
Generate verse embeddings for semantic search
Run on desktop/laptop with PyTorch support
"""

import sqlite3
import numpy as np
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Configuration
DB_FILE = "bible.db"
MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dims
OUTPUT_DIR = Path("embeddings")
BATCH_SIZE = 32

def load_verses_from_db():
    """Load all verses with metadata from database"""
    print("Loading verses from database...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            v.verse_id,
            b.book_name,
            b.book_number,
            b.testament,
            v.chapter,
            v.verse,
            v.text
        FROM verses v
        JOIN books b ON v.book_id = b.book_id
        ORDER BY b.book_number, v.chapter, v.verse
    """)

    verses = []
    for row in cursor.fetchall():
        verses.append({
            'verse_id': row[0],
            'book': row[1],
            'book_number': row[2],
            'testament': row[3],
            'chapter': row[4],
            'verse': row[5],
            'text': row[6],
            'reference': f"{row[1]} {row[4]}:{row[5]}"
        })

    conn.close()
    print(f"Loaded {len(verses)} verses")
    return verses

def load_cross_references(conn):
    """Load cross-reference counts for enrichment"""
    print("Loading cross-reference data...")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT from_verse_id, COUNT(*) as xref_count
        FROM cross_references
        GROUP BY from_verse_id
    """)

    xref_counts = dict(cursor.fetchall())
    print(f"Loaded cross-reference data for {len(xref_counts)} verses")
    return xref_counts

def create_embedding_text(verse, include_context=True, include_testament=True):
    """
    Create enriched text for embedding with multiple context levels

    Strategies:
    1. Basic: Just the verse text
    2. With context: Book Chapter:Verse - text
    3. With testament: [Testament] Book Chapter:Verse - text
    """
    text = verse['text']

    if not include_context:
        return text

    # Add book/chapter/verse reference
    contextual_text = f"{verse['reference']} - {text}"

    if include_testament:
        # Add testament context for broader categorization
        contextual_text = f"[{verse['testament']} Testament] {contextual_text}"

    return contextual_text

def generate_embeddings(verses, model_name=MODEL_NAME):
    """Generate embeddings for all verses"""
    print(f"\nLoading embedding model: {model_name}")
    print("This may take a few minutes on first run (downloading model)...")
    model = SentenceTransformer(model_name)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Strategy 1: Full context embeddings (best for general search)
    print("\nGenerating embeddings with full context...")
    texts_full = [create_embedding_text(v, include_context=True, include_testament=True)
                  for v in verses]

    embeddings_full = model.encode(
        texts_full,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # Strategy 2: Book context only (good for within-book search)
    print("\nGenerating embeddings with book context...")
    texts_book = [create_embedding_text(v, include_context=True, include_testament=False)
                  for v in verses]

    embeddings_book = model.encode(
        texts_book,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # Strategy 3: Text only (pure semantic matching)
    print("\nGenerating embeddings for text only...")
    texts_plain = [v['text'] for v in verses]

    embeddings_plain = model.encode(
        texts_plain,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    return {
        'full_context': embeddings_full,
        'book_context': embeddings_book,
        'text_only': embeddings_plain
    }, texts_full, texts_book, texts_plain

def save_embeddings(embeddings_dict, verses, texts_dict):
    """Save embeddings and metadata"""
    print("\nSaving embeddings...")

    # Save each embedding strategy
    for strategy, embeddings in embeddings_dict.items():
        np.save(OUTPUT_DIR / f"embeddings_{strategy}.npy", embeddings)
        print(f"  Saved {strategy}: {embeddings.shape}")

    # Save metadata
    metadata = {
        'verses': verses,
        'model_name': MODEL_NAME,
        'embedding_dim': embeddings_dict['full_context'].shape[1],
        'num_verses': len(verses),
        'strategies': list(embeddings_dict.keys())
    }

    with open(OUTPUT_DIR / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved metadata for {len(verses)} verses")

    # Save sample texts for debugging
    samples = {
        'full_context': texts_dict['full'][:5],
        'book_context': texts_dict['book'][:5],
        'text_only': texts_dict['plain'][:5]
    }

    with open(OUTPUT_DIR / "sample_texts.json", 'w', encoding='utf-8') as f:
        json.dump(samples, f, indent=2)

def main():
    """Main execution"""
    print("="*60)
    print("Bible Verse Embedding Generator")
    print("="*60)

    # Check if database exists
    if not Path(DB_FILE).exists():
        print(f"\nError: Database file '{DB_FILE}' not found!")
        print("Please ensure you're in the bible-schematic directory")
        return

    # Load data
    verses = load_verses_from_db()

    if not verses:
        print("Error: No verses found in database!")
        return

    # Generate embeddings
    embeddings_dict, texts_full, texts_book, texts_plain = generate_embeddings(verses)

    texts_dict = {
        'full': texts_full,
        'book': texts_book,
        'plain': texts_plain
    }

    # Save results
    save_embeddings(embeddings_dict, verses, texts_dict)

    # Summary
    print("\n" + "="*60)
    print("Embedding Generation Complete!")
    print("="*60)
    print(f"Verses processed: {len(verses):,}")
    print(f"Embedding dimensions: {embeddings_dict['full_context'].shape[1]}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print("\nFiles created:")
    print("  - embeddings_full_context.npy")
    print("  - embeddings_book_context.npy")
    print("  - embeddings_text_only.npy")
    print("  - metadata.json")
    print("  - sample_texts.json")
    print("\nNext step: Run build_faiss_index.py")
    print("="*60)

if __name__ == "__main__":
    main()
