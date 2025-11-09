#!/usr/bin/env python3
"""
Bible Semantic Search System
Complete interface with search, Q&A, similar verses, and theme extraction
"""

import numpy as np
import json
import sqlite3
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from typing import List, Dict, Optional

class BibleSearch:
    """Main search interface for Bible verses"""

    def __init__(self, strategy="full_context", model_name="all-MiniLM-L6-v2"):
        """Initialize search system"""
        self.strategy = strategy
        self.model_name = model_name
        self.faiss_dir = Path("faiss_index")
        self.db_file = "bible.db"

        print(f"Loading Bible Search System ({strategy})...")

        # Load model
        print("  Loading embedding model...")
        self.model = SentenceTransformer(model_name)

        # Load FAISS index
        print("  Loading FAISS index...")
        index_file = self.faiss_dir / f"bible_{strategy}.index"
        self.index = faiss.read_index(str(index_file))

        # Load metadata
        metadata_file = self.faiss_dir / f"{strategy}_metadata.json"
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)

        self.verses = self.metadata['verses']

        print(f"  Ready! Loaded {len(self.verses)} verses")

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a search query"""
        embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(embedding)
        return embedding

    def search(self, query: str, top_k: int = 10, testament: Optional[str] = None,
               books: Optional[List[str]] = None, min_score: float = 0.0) -> List[Dict]:
        """
        Semantic search for verses

        Args:
            query: Search query (e.g., "verses about love and sacrifice")
            top_k: Number of results to return
            testament: Filter by "Old" or "New" testament
            books: Filter by specific book names
            min_score: Minimum similarity score (0-1)

        Returns:
            List of verse dictionaries with scores
        """
        # Embed query
        query_vector = self._embed_query(query)

        # Search index (get more than needed for filtering)
        search_k = min(top_k * 10, len(self.verses))
        distances, indices = self.index.search(query_vector, search_k)

        # Collect and filter results
        results = []
        for idx, score in zip(indices[0], distances[0]):
            verse = self.verses[idx].copy()
            verse['score'] = float(score)

            # Apply filters
            if testament and verse['testament'] != testament:
                continue
            if books and verse['book'] not in books:
                continue
            if score < min_score:
                continue

            results.append(verse)

            if len(results) >= top_k:
                break

        return results

    def find_similar(self, book: str, chapter: int, verse_num: int,
                     top_k: int = 10) -> List[Dict]:
        """
        Find verses similar to a specific verse

        Args:
            book: Book name (e.g., "John")
            chapter: Chapter number
            verse_num: Verse number
            top_k: Number of similar verses to return

        Returns:
            List of similar verses with scores
        """
        # Find the verse in our data
        verse_idx = None
        for i, v in enumerate(self.verses):
            if v['book'] == book and v['chapter'] == chapter and v['verse'] == verse_num:
                verse_idx = i
                break

        if verse_idx is None:
            return []

        # Get the verse's embedding from index
        verse_vector = np.array([self.index.reconstruct(verse_idx)])
        faiss.normalize_L2(verse_vector)

        # Search for similar verses
        distances, indices = self.index.search(verse_vector, top_k + 1)

        # Return results (skip first since it's the query verse itself)
        results = []
        for idx, score in zip(indices[0][1:], distances[0][1:]):
            verse = self.verses[idx].copy()
            verse['score'] = float(score)
            results.append(verse)

        return results

    def answer_question(self, question: str, top_k: int = 5,
                       include_context: bool = True) -> Dict:
        """
        Q&A system: Answer a question using relevant verses

        Args:
            question: Question to answer (e.g., "What does the Bible say about faith?")
            top_k: Number of relevant verses to retrieve
            include_context: Include cross-references and analysis

        Returns:
            Dictionary with answer, relevant verses, and metadata
        """
        # Search for relevant verses
        verses = self.search(question, top_k=top_k)

        if not verses:
            return {
                'question': question,
                'answer': "No relevant verses found.",
                'verses': [],
                'confidence': 0.0
            }

        # Build answer
        answer_parts = []
        for i, v in enumerate(verses, 1):
            answer_parts.append(
                f"{i}. {v['reference']}: \"{v['text']}\" (relevance: {v['score']:.2f})"
            )

        answer = "\n\n".join(answer_parts)

        # Calculate confidence
        avg_score = sum(v['score'] for v in verses) / len(verses)

        result = {
            'question': question,
            'answer': answer,
            'verses': verses,
            'confidence': float(avg_score),
            'num_verses': len(verses)
        }

        # Add cross-references if requested
        if include_context:
            result['cross_references'] = self._get_cross_refs_for_verses(verses)

        return result

    def _get_cross_refs_for_verses(self, verses: List[Dict]) -> Dict:
        """Get cross-references for a list of verses"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        all_xrefs = {}
        for verse in verses:
            cursor.execute("""
                SELECT to_book, to_chapter, to_verse
                FROM verse_cross_references
                WHERE from_book = ? AND from_chapter = ? AND from_verse = ?
                ORDER BY votes DESC
                LIMIT 5
            """, (verse['book'], verse['chapter'], verse['verse']))

            xrefs = [f"{row[0]} {row[1]}:{row[2]}" for row in cursor.fetchall()]
            if xrefs:
                all_xrefs[verse['reference']] = xrefs

        conn.close()
        return all_xrefs

    def extract_themes(self, num_themes: int = 10, verses_per_theme: int = 5) -> List[Dict]:
        """
        Extract major themes by clustering verses

        Args:
            num_themes: Number of themes to identify
            verses_per_theme: Number of example verses per theme

        Returns:
            List of theme dictionaries with representative verses
        """
        print(f"Extracting {num_themes} themes from {len(self.verses)} verses...")

        # Get all embeddings from index
        embeddings = []
        for i in range(len(self.verses)):
            embeddings.append(self.index.reconstruct(i))

        embeddings = np.array(embeddings)

        # Perform clustering
        print("  Clustering verses...")
        kmeans = KMeans(n_clusters=num_themes, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Analyze each cluster
        themes = []
        for theme_id in range(num_themes):
            # Get verses in this cluster
            cluster_indices = np.where(labels == theme_id)[0]

            # Find verses closest to centroid
            centroid = kmeans.cluster_centers_[theme_id:theme_id+1]
            faiss.normalize_L2(centroid)

            # Calculate distances to centroid
            cluster_embeddings = embeddings[cluster_indices]
            faiss.normalize_L2(cluster_embeddings)

            distances = np.dot(cluster_embeddings, centroid.T).flatten()
            top_indices = cluster_indices[np.argsort(distances)[-verses_per_theme:]]

            # Get representative verses
            representative_verses = [self.verses[i] for i in reversed(top_indices)]

            # Generate theme description (use most central verses)
            theme_desc = self._generate_theme_description(representative_verses)

            themes.append({
                'theme_id': theme_id,
                'description': theme_desc,
                'num_verses': len(cluster_indices),
                'representative_verses': representative_verses,
                'testament_split': self._count_testaments(cluster_indices)
            })

        # Sort by cluster size
        themes.sort(key=lambda x: x['num_verses'], reverse=True)

        print(f"  Identified {num_themes} themes")
        return themes

    def _count_testaments(self, indices: np.ndarray) -> Dict:
        """Count Old vs New Testament verses in a cluster"""
        old, new = 0, 0
        for idx in indices:
            if self.verses[idx]['testament'] == "Old":
                old += 1
            else:
                new += 1
        return {"Old": old, "New": new}

    def _generate_theme_description(self, verses: List[Dict]) -> str:
        """Generate a description for a theme based on representative verses"""
        # Simple heuristic: use book names and common words
        books = set(v['book'] for v in verses)
        book_str = ", ".join(list(books)[:3])

        if len(books) > 3:
            book_str += ", etc."

        return f"Theme from {book_str}"

    def search_with_xrefs(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Enhanced search that includes traditional cross-references

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of verses with both semantic matches and cross-refs
        """
        # Get semantic search results
        results = self.search(query, top_k=top_k)

        # Add cross-references
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        for verse in results:
            cursor.execute("""
                SELECT to_book, to_chapter, to_verse, votes
                FROM verse_cross_references
                WHERE from_book = ? AND from_chapter = ? AND from_verse = ?
                ORDER BY votes DESC
                LIMIT 5
            """, (verse['book'], verse['chapter'], verse['verse']))

            xrefs = [{
                'reference': f"{row[0]} {row[1]}:{row[2]}",
                'votes': row[3]
            } for row in cursor.fetchall()]

            verse['cross_refs'] = xrefs

        conn.close()
        return results

def main():
    """Example usage"""
    print("="*60)
    print("Bible Semantic Search - Demo")
    print("="*60 + "\n")

    # Initialize
    searcher = BibleSearch()

    # Example 1: Semantic Search
    print("\n" + "="*60)
    print("EXAMPLE 1: Semantic Search")
    print("="*60)
    query = "love and sacrifice"
    print(f"Query: '{query}'\n")

    results = searcher.search(query, top_k=3)
    for i, verse in enumerate(results, 1):
        print(f"{i}. {verse['reference']} (score: {verse['score']:.3f})")
        print(f"   {verse['text']}\n")

    # Example 2: Find Similar Verses
    print("\n" + "="*60)
    print("EXAMPLE 2: Similar Verses")
    print("="*60)
    print("Finding verses similar to John 3:16\n")

    similar = searcher.find_similar("John", 3, 16, top_k=3)
    for i, verse in enumerate(similar, 1):
        print(f"{i}. {verse['reference']} (similarity: {verse['score']:.3f})")
        print(f"   {verse['text']}\n")

    # Example 3: Q&A
    print("\n" + "="*60)
    print("EXAMPLE 3: Question Answering")
    print("="*60)
    question = "What does the Bible say about faith?"
    print(f"Question: {question}\n")

    answer = searcher.answer_question(question, top_k=2)
    print(f"Answer (confidence: {answer['confidence']:.2f}):")
    print(answer['answer'])

    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
