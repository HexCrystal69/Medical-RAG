"""
FAISS Vector Store Module
-------------------------
Builds, saves, loads, and queries a FAISS index
backed by LangChain documents and HuggingFace embeddings.
"""

import os
from typing import List, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config import (
    RETRIEVAL_FETCH_K,
    RETRIEVAL_K,
    RERANK_FETCH_K,
    SIMILARITY_THRESHOLD,
    INDEX_DIR,
)


class FAISSStore:
    """Manages a FAISS vector store for document retrieval."""

    def __init__(
        self,
        embeddings: HuggingFaceEmbeddings,
        index_dir: str = INDEX_DIR,
    ) -> None:
        self.embeddings = embeddings
        self.index_dir = index_dir
        self.vectorstore: Optional[FAISS] = None

    def build_index(self, documents: List[Document], ids: Optional[List[str]] = None) -> FAISS:
        if not documents:
            raise ValueError("Cannot build an index from an empty document list.")

        print(f"[INFO] Building FAISS index from {len(documents)} document chunks …")
        self.vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings,
            ids=ids
        )
        print("[INFO] FAISS index built successfully.")
        return self.vectorstore

    def add_documents(self, documents: List[Document], ids: List[str]) -> None:
        """Add documents incrementally to the FAISS index."""
        if not documents:
            return
        if self.vectorstore is None:
            self.build_index(documents, ids=ids)
        else:
            print(f"[INFO] Incrementally adding {len(documents)} document chunks to FAISS …")
            self.vectorstore.add_documents(documents, ids=ids)
            print("[INFO] Document chunks added successfully.")

    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents by their IDs from the FAISS index."""
        if self.vectorstore is None:
            raise RuntimeError("No FAISS index available to delete from.")
        print(f"[INFO] Deleting {len(ids)} chunks from FAISS index …")
        try:
            self.vectorstore.delete(ids=ids)
            print("[INFO] Chunks deleted successfully.")
        except Exception as exc:
            # Handle potential empty index / deletion issues gracefully
            print(f"[ERROR] Failed to delete chunks from FAISS: {exc}")

    def save_index(self, directory: Optional[str] = None) -> str:
        if self.vectorstore is None:
            raise RuntimeError("No index to save. Call build_index() first.")

        save_path = directory or self.index_dir
        self.vectorstore.save_local(save_path)
        print(f"[INFO] FAISS index saved to: {os.path.abspath(save_path)}")
        return save_path

    def load_index(self, directory: Optional[str] = None) -> FAISS:
        load_path = directory or self.index_dir
        if not os.path.isdir(load_path) or not os.path.exists(os.path.join(load_path, "index.faiss")):
            raise FileNotFoundError(f"Index directory not found or index.faiss missing: {load_path}")

        self.vectorstore = FAISS.load_local(
            load_path,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"[INFO] FAISS index loaded from: {os.path.abspath(load_path)}")
        return self.vectorstore

    def similarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> List[Document]:
        if self.vectorstore is None:
            raise RuntimeError("No index available. Build or load an index first.")
        results = self.vectorstore.similarity_search(query, k=k)
        return results

    def mmr_search(
        self,
        query: str,
        k: int = RETRIEVAL_K,
        fetch_k: int = RETRIEVAL_FETCH_K,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        if self.vectorstore is None:
            raise RuntimeError("No index available. Build or load an index first.")
        return self.vectorstore.max_marginal_relevance_search(
            query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
        )

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = RERANK_FETCH_K,
    ) -> List[Tuple[Document, float]]:
        if self.vectorstore is None:
            return []

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        # Convert L2 distance to similarity score: 1 / (1 + dist)
        scored = [
            (doc, 1.0 / (1.0 + dist))
            for doc, dist in results
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def retrieve(
        self,
        query: str,
        k: int = RERANK_FETCH_K,
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> List[Tuple[Document, float]]:
        scored_docs = self.similarity_search_with_scores(query, k=k)
        filtered = [
            (doc, score) for doc, score in scored_docs
            if score >= threshold
        ]
        return filtered
