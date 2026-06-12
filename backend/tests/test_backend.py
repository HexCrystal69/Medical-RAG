"""
Automated Backend Verification Test Suite
==========================================
Validates key modules like Local BM25, RRF hybrid fusion, confidence checks,
and API routing without reloading heavy deep learning weights (using mocks).
"""

import unittest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retriever.hybrid_retriever import BM25RetrieverLocal, HybridRetriever
from rag.retrieval_chain import RetrievalChain, RAGResult, SourceInfo


class TestBM25Retriever(unittest.TestCase):
    """Verifies lightweight local BM25 ranking and matching."""

    def test_bm25_relevance(self):
        docs = [
            Document(page_content="Type 2 diabetes is a chronic metabolic disease characterized by high blood sugar."),
            Document(page_content="Asthma and COPD are common respiratory diseases affecting lung airflow."),
            Document(page_content="Lisinopril is an ACE inhibitor medication used to treat hypertension.")
        ]
        retriever = BM25RetrieverLocal(docs)
        
        # Test search match
        results = retriever.retrieve("diabetes blood sugar", k=2)
        self.assertTrue(len(results) > 0)
        self.assertIn("diabetes", results[0][0].page_content.lower())
        
        # Test non-matching query
        empty_res = retriever.retrieve("ebola symptoms", k=5)
        # BM25 scores non-matching terms as 0.0
        self.assertEqual(empty_res[0][1], 0.0)


class TestHybridRetrieverRRF(unittest.TestCase):
    """Verifies Reciprocal Rank Fusion (RRF) logic and rank consolidation."""

    def test_rrf_scoring(self):
        docs = [
            Document(page_content="Document Alpha about asthma therapy"),
            Document(page_content="Document Beta about cardiac treatment"),
        ]
        
        # Mock FAISS store retrieve method
        mock_faiss = MagicMock()
        mock_faiss.retrieve.return_value = [(docs[0], 0.85)]
        
        retriever = HybridRetriever(mock_faiss, docs)
        
        # Query with hybrid strategy
        results = retriever.retrieve("asthma therapy", k=2, strategy="hybrid", threshold=0.50)
        
        self.assertTrue(len(results) > 0)
        # Should return Document Alpha as top hit
        self.assertEqual(results[0][0].page_content, docs[0].page_content)


class TestRetrievalChainGates(unittest.TestCase):
    """Verifies confidence checks and fallback triggers inside the retrieval chain."""

    def test_grounded_rejection_without_fallback(self):
        # Setup mocks
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [] # no documents match
        
        mock_reranker = MagicMock()
        mock_llm = MagicMock()
        
        chain = RetrievalChain(
            retriever=mock_retriever,
            reranker=mock_reranker,
            llm_client=mock_llm,
            threshold=0.60,
            fallback_enabled=False
        )

        result = chain.query("What is the capital of France?", stream=False)
        self.assertTrue(result.is_insufficient)
        self.assertIn("not contain enough information", result.answer)
        self.assertFalse(result.is_fallback)

    def test_grounded_fallback_enabled(self):
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        
        mock_reranker = MagicMock()
        
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Paris is the capital of France."
        
        chain = RetrievalChain(
            retriever=mock_retriever,
            reranker=mock_reranker,
            llm_client=mock_llm,
            threshold=0.60,
            fallback_enabled=True
        )

        result = chain.query("What is the capital of France?", stream=False)
        self.assertTrue(result.is_fallback)
        self.assertEqual(result.answer, "Paris is the capital of France.")


if __name__ == "__main__":
    unittest.main()
