# Vector Database Setup Guide

This guide explains how to set up semantic search over the NKJV Bible using FAISS and sentence-transformers.

## Overview

The vector database enables:
- **Semantic Search**: Find verses by meaning, not just keywords
- **Similar Verses**: Discover related verses based on content
- **Q&A System**: Ask questions and get relevant verse answers
- **Theme Extraction**: Automatically group verses by theological themes

## Architecture

```
Bible Database (SQLite)
    ↓
Verse Embeddings (sentence-transformers)
    ↓
FAISS Vector Index
    ↓
Search/Query Interface
```

## Prerequisites

**⚠️ Important**: This requires PyTorch, which doesn't run on Android/Termux. Run on a desktop/laptop with:
- Python 3.8+
- 4GB+ RAM
- 2GB+ free disk space

## Installation

### 1. Install Dependencies

```bash
# On desktop/laptop (NOT Termux)
pip install -r vector_requirements.txt
```

### 2. Generate Embeddings

```bash
python generate_embeddings.py
```

This will:
- Load all 30,642 verses from the database
- Generate embeddings using sentence-transformers
- Create enriched text with book/chapter context
- Save embeddings to `embeddings/verse_embeddings.npy`
- Expected time: 10-20 minutes

### 3. Build FAISS Index

```bash
python build_faiss_index.py
```

Creates:
- `faiss_index/bible.index` - FAISS vector index
- `faiss_index/metadata.json` - Verse metadata mapping

### 4. Test Search

```bash
python search_bible.py "verses about hope and faith"
```

## Embedding Strategy

We embed verses with three levels of context:

###  1. Individual Verses
```python
text = verse_text
# Example: "For God so loved the world..."
```

### 2. Verse with Context
```python
text = f"{book_name} {chapter}:{verse} - {verse_text}"
# Example: "John 3:16 - For God so loved the world..."
```

### 3. Verse with Testament Context
```python
text = f"[{testament} Testament] {book_name} {chapter}:{verse} - {verse_text}"
# Example: "[New Testament] John 3:16 - For God so loved the world..."
```

## Model Selection

**Default Model**: `all-MiniLM-L6-v2`
- Embedding size: 384 dimensions
- Speed: Fast (~14k sentences/sec on CPU)
- Quality: Excellent for semantic search
- Size: 80MB

**Alternative Models**:
- `all-mpnet-base-v2`: Better quality, slower (768 dims)
- `paraphrase-MiniLM-L3-v2`: Faster, smaller (384 dims)
- `multi-qa-MiniLM-L6-cos-v1`: Optimized for Q&A

## Usage Examples

### Semantic Search
```python
from bible_search import BibleSearch

searcher = BibleSearch()

# Find verses by meaning
results = searcher.search("verses about love and sacrifice", top_k=5)
for verse in results:
    print(f"{verse['reference']}: {verse['text']}")
    print(f"Similarity: {verse['score']:.3f}\n")
```

### Similar Verses
```python
# Find verses similar to John 3:16
similar = searcher.find_similar("John", 3, 16, top_k=10)
```

### Q&A System
```python
# Ask a question
answer = searcher.answer_question("What does the Bible say about faith?")
```

### Theme Extraction
```python
# Group verses by theme
themes = searcher.extract_themes(num_themes=10)
```

## File Structure

```
bible-schematic/
├── bible.db                          # SQLite database
├── generate_embeddings.py            # Create verse embeddings
├── build_faiss_index.py             # Build FAISS index
├── bible_search.py                  # Search interface
├── vector_requirements.txt          # Python dependencies
├── embeddings/                      # Generated embeddings
│   ├── verse_embeddings.npy
│   ├── verse_metadata.json
│   └── model_info.json
└── faiss_index/                     # FAISS index files
    ├── bible.index
    └── metadata.json
```

## Performance

**Embedding Generation**:
- 30,642 verses
- ~384 dims per verse
- Time: 10-20 minutes (CPU)
- Storage: ~50MB

**Search Performance**:
- Index size: ~50MB in memory
- Query time: <100ms for top-10 results
- Can handle 1000+ queries/second

## Cross-References Integration

The system integrates with the existing cross-reference database:

```python
# Get semantically similar verses + traditional cross-refs
results = searcher.search_with_xrefs("faith and works", top_k=5)

for result in results:
    print(f"{result['reference']}: {result['text']}")
    print(f"Traditional cross-refs: {result['cross_refs']}")
    print(f"Semantic similarity: {result['similarity']:.3f}\n")
```

## Advanced Features

### Custom Embeddings
```python
# Use your own embedding model
searcher = BibleSearch(model_name="paraphrase-multilingual-MiniLM-L12-v2")
```

### Filtered Search
```python
# Search only New Testament
results = searcher.search("grace", testament="New", top_k=10)

# Search specific books
results = searcher.search("prophecy", books=["Isaiah", "Jeremiah"], top_k=10)
```

### Clustering
```python
# Find verse clusters
clusters = searcher.cluster_verses(num_clusters=50)
```

## Troubleshooting

### Out of Memory
- Reduce batch size in `generate_embeddings.py`
- Use smaller model (`paraphrase-MiniLM-L3-v2`)

### Slow Generation
- Use GPU if available
- Reduce number of verses (sample subset first)

### Poor Search Results
- Try different embedding model
- Adjust search parameters (top_k, threshold)
- Include more context in verse text

## Future Enhancements

- [ ] Multi-language support (Greek, Hebrew)
- [ ] Fine-tuned model on theological texts
- [ ] Integration with study notes
- [ ] Verse recommendation system
- [ ] Topical Bible generation

## Resources

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [FAISS Documentation](https://faiss.ai/)
- [Model Hub](https://huggingface.co/sentence-transformers)

---

*This setup is ready to run on any desktop/laptop with Python. Transfer the database file and run the scripts!*
