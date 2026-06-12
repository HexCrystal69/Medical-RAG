"""
FastAPI Routes — RAG Query Pipeline
====================================
Exposes query endpoints with performance metrics tracking and analytics logs.
"""

import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from utils.exporter import Exporter

router = APIRouter(prefix="/query", tags=["Query"])

class QueryRequest(BaseModel):
    question: str
    strategy: str = "hybrid"  # vector, bm25, hybrid

class SourceResponse(BaseModel):
    filename: str
    page_number: int
    similarity_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceResponse]
    confidence_score: float
    is_fallback: bool
    retrieval_strategy: str
    latencies: Dict[str, float]

@router.post("", response_model=QueryResponse)
async def query_pipeline(request: QueryRequest):
    """Run the complete hybrid RAG pipeline for the given question and strategy."""
    from main import get_retrieval_chain, get_tracker
    
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    chain = get_retrieval_chain()
    tracker = get_tracker()

    # Time retrieval
    t_start = time.time()
    
    # Run query (non-streaming for API convenience, but fast local execution)
    try:
        # Measure retrieval duration separately by replicating parts or timing query
        t_ret_start = time.time()
        scored_docs = chain.retriever.retrieve(
            question,
            k=chain.retrieval_k,
            strategy=request.strategy,
            threshold=chain.threshold
        )
        retrieval_time = time.time() - t_ret_start

        # Execute full query
        result = chain.query(question, stream=False, strategy=request.strategy)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {exc}")

    total_time = time.time() - t_start
    inference_time = max(total_time - retrieval_time, 0.0)

    # Cited documents list
    cited_docs = list({src.filename for src in result.sources})

    # Determine success status (failed if RAG had insufficient info)
    success = not result.is_insufficient

    # Log query analytics
    try:
        tracker.log_query(
            query=question,
            retrieval_time=retrieval_time,
            inference_time=inference_time,
            referenced_docs=cited_docs,
            success=success,
            strategy=request.strategy
        )
    except Exception as exc:
        print(f"[WARNING] Failed to log query to tracker: {exc}")

    sources_response = [
        SourceResponse(
            filename=src.filename,
            page_number=src.page_number,
            similarity_score=src.similarity_score
        )
        for src in result.sources
    ]

    return QueryResponse(
        answer=result.answer,
        sources=sources_response,
        confidence_score=result.confidence,
        is_fallback=result.is_fallback,
        retrieval_strategy=result.retrieval_strategy,
        latencies={
            "retrieval_time": round(retrieval_time, 4),
            "inference_time": round(inference_time, 4),
            "total_time": round(total_time, 4)
        }
    )

class ExportQueryRequest(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]] = []
    format: str = "txt"

@router.post("/export")
async def export_query_answer(request: ExportQueryRequest):
    """Export a medical query answer as plain text or PDF."""
    sources_text = ""
    if request.sources:
        sources_text = "\n".join([f"* {s.get('filename')} (page {s.get('page_number')})" for s in request.sources])
    else:
        sources_text = "No sources cited (General Knowledge Fallback)."

    sections = [
        {"header": "Question", "body": request.question},
        {"header": "Answer", "body": request.answer},
        {"header": "Sources Cited", "body": sources_text}
    ]
    title = f"Medical Query Report"

    if request.format == "pdf":
        file_bytes = Exporter.to_pdf(title, sections)
        media_type = "application/pdf"
        filename = "medical_query_report.pdf"
    else:
        file_bytes = Exporter.to_txt(title, sections)
        media_type = "text/plain"
        filename = "medical_query_report.txt"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

