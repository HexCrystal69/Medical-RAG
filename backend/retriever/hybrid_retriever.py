"""
Hybrid Retriever Module
------------------------
Implements term-based BM25 search alongside FAISS semantic search.
Combines results using Reciprocal Rank Fusion (RRF).
"""

import math
from typing import List, Dict, Tuple, Optional
from langchain_core.documents import Document

from config import RERANK_FETCH_K


class BM25RetrieverLocal:
    """A lightweight, zero-dependency Python implementation of BM25 search."""

    def __init__(self, documents: List[Document], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_len = [len(self.tokenize(doc.page_content)) for doc in documents]
        self.avg_doc_len = sum(self.doc_len) / len(documents) if documents else 0
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.corpus_size = len(documents)
        self.build_index()

    def tokenize(self, text: str) -> List[str]:
        # Simple lowercase word boundary tokenizer
        return [w.lower() for w in text.replace(".", " ").replace(",", " ").replace("-", " ").split() if w]

    def build_index(self) -> None:
        df: Dict[str, int] = {}
        for doc in self.documents:
            tokens = self.tokenize(doc.page_content)
            freqs: Dict[str, int] = {}
            for t in tokens:
                freqs[t] = freqs.get(t, 0) + 1
            self.doc_freqs.append(freqs)
            for t in freqs:
                df[t] = df.get(t, 0) + 1

        for term, freq in df.items():
            self.idf[term] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def retrieve(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        query_tokens = self.tokenize(query)
        if not self.documents or not query_tokens:
            return []

        scores = []
        for idx, freqs in enumerate(self.doc_freqs):
            score = 0.0
            doc_len = self.doc_len[idx]
            for term in query_tokens:
                if term in freqs:
                    tf = freqs[term]
                    idf = self.idf.get(term, 0.0)
                    numerator = idf * tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
                    score += numerator / denominator
            # Clamp or scale score slightly if wanted, but keep raw floats
            scores.append((self.documents[idx], score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class HybridRetriever:
    """Combines semantic search (FAISS) and keyword search (BM25) using RRF."""

    def __init__(self, faiss_store, documents: List[Document]):
        self.faiss_store = faiss_store
        self.documents = documents
        self.bm25 = BM25RetrieverLocal(documents) if documents else None

    def update_documents(self, documents: List[Document]) -> None:
        """Incrementally update BM25 search corpus."""
        self.documents = documents
        if documents:
            self.bm25 = BM25RetrieverLocal(documents)
        else:
            self.bm25 = None

    def retrieve(
        self,
        query: str,
        k: int = RERANK_FETCH_K,
        strategy: str = "hybrid",
        threshold: float = 0.60
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve documents using the selected strategy.

        Strategies:
            - 'vector': Only FAISS semantic retrieval
            - 'bm25': Only BM25 term retrieval
            - 'hybrid': FAISS + BM25 combined via Reciprocal Rank Fusion (RRF)
        """
        # Strategy fallback if no index is loaded
        if not self.documents:
            return []

        if strategy == "vector":
            return self.faiss_store.retrieve(query, k=k, threshold=threshold)

        if strategy == "bm25":
            if not self.bm25:
                return []
            bm25_results = self.bm25.retrieve(query, k=k)
            # Normalize BM25 scores to [0.0, 1.0] for threshold comparison
            if not bm25_results:
                return []
            max_score = max(score for _, score in bm25_results)
            normalized = []
            for doc, score in bm25_results:
                norm_score = (score / max_score) if max_score > 0 else 0.5
                # Map to a reasonable cosine range
                mapped_score = 0.5 + 0.45 * norm_score
                if mapped_score >= threshold:
                    normalized.append((doc, mapped_score))
            return normalized

        # Hybrid Strategy (RRF)
        vector_results = self.faiss_store.retrieve(query, k=k, threshold=threshold)
        bm25_results = self.bm25.retrieve(query, k=k) if self.bm25 else []

        # Map page contents to docs and scores to preserve original records
        doc_map: Dict[str, Document] = {}
        vector_scores: Dict[str, float] = {}

        for doc, score in vector_results:
            key = doc.page_content
            doc_map[key] = doc
            vector_scores[key] = score

        for doc, score in bm25_results:
            key = doc.page_content
            doc_map[key] = doc

        # Calculate RRF ranks (1-indexed)
        rrf_scores: Dict[str, float] = {}
        c = 60  # constant

        # Process vector ranks
        for rank, (doc, _) in enumerate(vector_results, 1):
            key = doc.page_content
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (c + rank))

        # Process BM25 ranks
        for rank, (doc, _) in enumerate(bm25_results, 1):
            key = doc.page_content
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (c + rank))

        if not rrf_scores:
            return []

        # Sort by RRF score descending
        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        max_rrf = sorted_rrf[0][1]

        final_results = []
        for key, rrf_score in sorted_rrf[:k]:
            doc = doc_map[key]
            # If it has a semantic score, use it; otherwise, synthesize using RRF ratio
            if key in vector_scores:
                score = vector_scores[key]
            else:
                ratio = rrf_score / max_rrf if max_rrf > 0 else 1.0
                score = 0.5 + 0.4 * ratio  # synthetically map between 0.50 and 0.90

            if score >= threshold:
                final_results.append((doc, score))

        return final_results
