"""
Retrieval Chain Module
-----------------------
Orchestrates the full RAG pipeline with hybrid search and fallback support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from langchain_core.documents import Document

from config import (
    INSUFFICIENT_INFO_MSG,
    RERANK_FETCH_K,
    RERANK_TOP_K,
    SIMILARITY_THRESHOLD,
    OLLAMA_FALLBACK_SYSTEM_PROMPT,
    DEFAULT_FALLBACK_ENABLED,
)
from llm.qwen_client import QwenOllamaClient
from reranker.cross_encoder import CrossEncoderReranker
from retriever.hybrid_retriever import HybridRetriever


@dataclass
class SourceInfo:
    """Metadata for a single retrieved source chunk."""
    filename: str
    page_number: int
    similarity_score: float
    rerank_score: float
    disease_category: str = "general"


@dataclass
class RAGResult:
    """Complete result of a RAG query."""
    query: str
    answer: str
    sources: List[SourceInfo] = field(default_factory=list)
    confidence: float = 0.0
    is_insufficient: bool = False
    is_fallback: bool = False
    retrieval_strategy: str = "hybrid"


class RetrievalChain:
    """
    End-to-end retrieval-augmented generation chain.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        llm_client: QwenOllamaClient,
        threshold: float = SIMILARITY_THRESHOLD,
        retrieval_k: int = RERANK_FETCH_K,
        rerank_top_k: int = RERANK_TOP_K,
        fallback_enabled: bool = DEFAULT_FALLBACK_ENABLED,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.llm_client = llm_client
        self.threshold = threshold
        self.retrieval_k = retrieval_k
        self.rerank_top_k = rerank_top_k
        self.fallback_enabled = fallback_enabled

    @staticmethod
    def _build_context(
        reranked: List[Tuple[Document, float, float]],
    ) -> str:
        parts: list[str] = []
        for i, (doc, sim_score, ce_score) in enumerate(reranked, 1):
            filename = doc.metadata.get("filename", doc.metadata.get("source", "unknown"))
            page = doc.metadata.get("page_number", doc.metadata.get("page", "?"))
            parts.append(
                f"[Source {i}: {filename}, Page {page}, Similarity {sim_score:.2f}]\n"
                f"{doc.page_content}"
            )
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _extract_sources(
        reranked: List[Tuple[Document, float, float]],
    ) -> List[SourceInfo]:
        sources: list[SourceInfo] = []
        for doc, sim_score, ce_score in reranked:
            sources.append(
                SourceInfo(
                    filename=doc.metadata.get("filename", doc.metadata.get("source", "unknown")),
                    page_number=doc.metadata.get("page_number", doc.metadata.get("page", 0)),
                    similarity_score=round(sim_score, 4),
                    rerank_score=round(ce_score, 4),
                    disease_category=doc.metadata.get("disease_category", "general"),
                )
            )
        return sources

    @staticmethod
    def _compute_confidence(
        reranked: List[Tuple[Document, float, float]],
    ) -> float:
        if not reranked:
            return 0.0
        scores = [sim for _, sim, _ in reranked]
        avg = sum(scores) / len(scores)
        return round(min(max(avg, 0.0), 1.0), 4)

    def query(
        self,
        question: str,
        stream: bool = True,
        strategy: str = "hybrid",
    ) -> RAGResult:
        """Run the full hybrid RAG pipeline for a user question."""
        # ── Step 1: Retrieve using the selected strategy ─────────────
        scored_docs = self.retriever.retrieve(
            question,
            k=self.retrieval_k,
            strategy=strategy,
            threshold=self.threshold,
        )

        if not scored_docs:
            if self.fallback_enabled:
                answer = self.llm_client.generate(question, stream=stream, system_prompt=OLLAMA_FALLBACK_SYSTEM_PROMPT)
                return RAGResult(
                    query=question,
                    answer=answer,
                    confidence=0.0,
                    is_fallback=True,
                    retrieval_strategy=strategy,
                )
            return RAGResult(
                query=question,
                answer=INSUFFICIENT_INFO_MSG,
                confidence=0.0,
                is_insufficient=True,
                retrieval_strategy=strategy,
            )

        # ── Step 2: Re-rank ──────────────────────────────────────────
        reranked = self.reranker.rerank(
            question, scored_docs, top_k=self.rerank_top_k
        )

        if not reranked:
            if self.fallback_enabled:
                answer = self.llm_client.generate(question, stream=stream, system_prompt=OLLAMA_FALLBACK_SYSTEM_PROMPT)
                return RAGResult(
                    query=question,
                    answer=answer,
                    confidence=0.0,
                    is_fallback=True,
                    retrieval_strategy=strategy,
                )
            return RAGResult(
                query=question,
                answer=INSUFFICIENT_INFO_MSG,
                confidence=0.0,
                is_insufficient=True,
                retrieval_strategy=strategy,
            )

        # ── Step 3: Confidence check ─────────────────────────────────
        confidence = self._compute_confidence(reranked)
        sources = self._extract_sources(reranked)

        if confidence < self.threshold:
            if self.fallback_enabled:
                answer = self.llm_client.generate(question, stream=stream, system_prompt=OLLAMA_FALLBACK_SYSTEM_PROMPT)
                return RAGResult(
                    query=question,
                    answer=answer,
                    sources=sources,
                    confidence=confidence,
                    is_fallback=True,
                    retrieval_strategy=strategy,
                )
            return RAGResult(
                query=question,
                answer=INSUFFICIENT_INFO_MSG,
                sources=sources,
                confidence=confidence,
                is_insufficient=True,
                retrieval_strategy=strategy,
            )

        # ── Step 4: Build prompt and generate ────────────────────────
        context = self._build_context(reranked)
        user_content = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer based ONLY on the context above. Cite filenames and page numbers."
        )

        answer = self.llm_client.generate(user_content, stream=stream)

        return RAGResult(
            query=question,
            answer=answer,
            sources=sources,
            confidence=confidence,
            is_insufficient=False,
            is_fallback=False,
            retrieval_strategy=strategy,
        )

    def clear_history(self) -> None:
        self.llm_client.clear_history()
