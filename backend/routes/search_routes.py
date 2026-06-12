"""
FastAPI Routes — Literature Search
===================================
Searches the database for passages without generating an LLM response.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/search", tags=["Search"])

class SearchRequest(BaseModel):
    query: str
    strategy: str = "hybrid"
    threshold: float = 0.60
    limit: int = 5

class SearchItem(BaseModel):
    passage: str
    filename: str
    page_number: int
    similarity_score: float
    disease_category: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchItem]
    retrieval_strategy: str

@router.post("", response_model=SearchResponse)
async def search_literature(request: SearchRequest):
    """Retrieve raw text passages matching the query, without invoking LLM generation."""
    from main import get_retriever
    
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    retriever = get_retriever()
    try:
        scored_docs = retriever.retrieve(
            query,
            k=request.limit,
            strategy=request.strategy,
            threshold=request.threshold
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search execution failed: {exc}")

    results = [
        SearchItem(
            passage=doc.page_content,
            filename=doc.metadata.get("filename", "unknown.pdf"),
            page_number=doc.metadata.get("page_number", doc.metadata.get("page", 0)),
            similarity_score=round(score, 4),
            disease_category=doc.metadata.get("disease_category", "general")
        )
        for doc, score in scored_docs
    ]

    return SearchResponse(
        query=query,
        results=results,
        retrieval_strategy=request.strategy
    )
