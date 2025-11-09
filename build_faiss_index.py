#!/usr/bin/env python3
"""
Build FAISS index from generated embeddings
Run after generate_embeddings.py
"""

import numpy as np
import json
import faiss
from pathlib import Path

# Configuration
EMBEDDINGS_DIR = Path("embeddings")
FAISS_DIR = Path("faiss_index")

def load_embeddings(strategy="full_context"):
    """Load embeddings and metadata"""
    print(f"Loading {strategy} embeddings...")

    embeddings_file = EMBEDDINGS_DIR / f"embeddings_{strategy}.npy"
    metadata_file = EMBEDDINGS_DIR / "metadata.json"

    if not embeddings_file.exists():
        raise FileNotFoundError(f"Embeddings not found: {embeddings_file}")

    embeddings = np.load(embeddings_file)

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    print(f"  Loaded {embeddings.shape[0]} embeddings of {embeddings.shape[1]} dimensions")
    return embeddings, metadata

def build_faiss_index(embeddings, use_gpu=False):
    """
    Build FAISS index for fast similarity search

    Index types:
    - Flat: Exact search, slower but accurate
    - IVF: Inverted file index, faster but approximate
    - HNSW: Hierarchical navigable small world, best balance
    """
    print("Building FAISS index...")

    dimension = embeddings.shape[0]
    n_vectors = embeddings.shape[0]

    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)

    # Choose index type based on dataset size
    if n_vectors < 10000:
        # Small dataset: use flat index (exact search)
        print("  Using Flat index (exact search)")
        index = faiss.IndexFlatIP(dimension)  # Inner Product = cosine after normalization
    else:
        # Larger dataset: use HNSW for speed
        print("  Using HNSW index (approximate search)")
        M = 32  # Number of connections per layer
        index = faiss.IndexHNSWFlat(dimension, M)
        index.hnsw.efConstruction = 40  # Build quality
        index.hnsw.efSearch = 16  # Search quality

    # Add vectors to index
    print(f"  Adding {n_vectors} vectors...")
    index.add(embeddings)

    print(f"  Index built! Total vectors: {index.ntotal}")
    return index

def save_index(index, metadata, strategy="full_context"):
    """Save FAISS index and metadata"""
    FAISS_DIR.mkdir(exist_ok=True)

    index_file = FAISS_DIR / f"bible_{strategy}.index"
    metadata_file = FAISS_DIR / f"{strategy}_metadata.json"

    print(f"\nSaving index to {index_file}...")
    faiss.write_index(index, str(index_file))

    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Saved successfully!")

def test_index(index, embeddings, metadata):
    """Quick test of the index"""
    print("\nTesting index...")

    # Search for similar verses to John 3:16
    john_316 = None
    for i, verse in enumerate(metadata['verses']):
        if verse['book'] == 'John' and verse['chapter'] == 3 and verse['verse'] == 16:
            john_316 = i
            break

    if john_316 is not None:
        # Search for 5 most similar verses
        query_vector = embeddings[john_316:john_316+1]
        faiss.normalize_L2(query_vector)

        distances, indices = index.search(query_vector, 6)  # 6 because first will be itself

        print(f"\n  Query: {metadata['verses'][john_316]['reference']}")
        print(f"  Text: {metadata['verses'][john_316]['text'][:80]}...")
        print("\n  Top 5 similar verses:")

        for i, (idx, dist) in enumerate(zip(indices[0][1:6], distances[0][1:6])):
            verse = metadata['verses'][idx]
            print(f"    {i+1}. {verse['reference']} (similarity: {dist:.3f})")
            print(f"       {verse['text'][:60]}...")

def main():
    """Main execution"""
    print("="*60)
    print("FAISS Index Builder")
    print("="*60 + "\n")

    # Check if embeddings exist
    if not EMBEDDINGS_DIR.exists():
        print(f"Error: Embeddings directory not found: {EMBEDDINGS_DIR}")
        print("Run generate_embeddings.py first!")
        return

    # Build index for each strategy
    strategies = ["full_context", "book_context", "text_only"]

    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"Building index for: {strategy}")
        print("="*60)

        try:
            # Load embeddings
            embeddings, metadata = load_embeddings(strategy)

            # Build index
            index = build_faiss_index(embeddings)

            # Save index
            save_index(index, metadata, strategy)

            # Test if this is the main strategy
            if strategy == "full_context":
                test_index(index, embeddings, metadata)

        except FileNotFoundError as e:
            print(f"  Skipping {strategy}: {e}")
            continue

    # Summary
    print("\n" + "="*60)
    print("Index Building Complete!")
    print("="*60)
    print(f"Output directory: {FAISS_DIR.absolute()}")
    print("\nNext step: Run bible_search.py to query the index")
    print("="*60)

if __name__ == "__main__":
    main()
