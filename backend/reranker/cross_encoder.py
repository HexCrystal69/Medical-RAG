"""
Cross-Encoder Re-Ranker Module
-------------------------------
Uses a cross-encoder model to re-score retriever candidates
and return only the most relevant chunks.
"""

from typing import List, Tuple

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder as _CrossEncoder

from config import CROSS_ENCODER_MODEL, DEVICE, RERANK_TOP_K


class CrossEncoderReranker:
    """Re-ranks retriever results using a cross-encoder model."""

    def __init__(
        self,
        model_name: str = CROSS_ENCODER_MODEL,
        device: str = DEVICE,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.model = _CrossEncoder(model_name, device=device)
        print(f"[INFO] Cross-encoder loaded: {model_name} (device={device})")

    def rerank(
        self,
        query: str,
        documents_with_scores: List[Tuple[Document, float]],
        top_k: int = RERANK_TOP_K,
    ) -> List[Tuple[Document, float, float]]:
        if not documents_with_scores:
            return []

        # Build (query, passage) pairs
        pairs = [
            (query, doc.page_content)
            for doc, _score in documents_with_scores
        ]

        ce_scores = self.model.predict(pairs)

        # Combine: (Document, retriever_score, cross_encoder_score)
        combined = [
            (doc, sim_score, float(ce_score))
            for (doc, sim_score), ce_score in zip(
                documents_with_scores, ce_scores
            )
        ]

        # Sort by cross-encoder score (descending)
        combined.sort(key=lambda x: x[2], reverse=True)

        return combined[:top_k]
