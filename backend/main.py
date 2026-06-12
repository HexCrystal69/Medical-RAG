"""
Medical Research Assistant — Backend Server
============================================
FastAPI application serving both REST API endpoints and static frontend pages.
Implements lazy-loading and caching of heavyweight neural models.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure the backend directory is in the path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import BASE_DIR as CONFIG_BASE_DIR

# --- Singletons Caching ---
_embedder = None
_faiss_store = None
_retriever = None
_llm_client = None
_reranker = None
_chain = None
_tracker = None
_evaluator = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from embeddings.embedder import Embedder
        _embedder = Embedder()
    return _embedder

def get_faiss_store():
    global _faiss_store
    if _faiss_store is None:
        from vectorstore.faiss_store import FAISSStore
        _faiss_store = FAISSStore(embeddings=get_embedder().get_embeddings())
        try:
            _faiss_store.load_index()
        except Exception as exc:
            print(f"[WARNING] FAISS index could not be loaded: {exc}. Index is currently empty.")
    return _faiss_store

def get_retriever():
    global _retriever
    if _retriever is None:
        from retriever.hybrid_retriever import HybridRetriever
        all_docs = []
        store = get_faiss_store()
        if store.vectorstore is not None:
            all_docs = list(store.vectorstore.docstore._dict.values())
        _retriever = HybridRetriever(store, all_docs)
    return _retriever

def get_llm_client():
    global _llm_client
    if _llm_client is None:
        from llm.qwen_client import QwenOllamaClient
        _llm_client = QwenOllamaClient()
    return _llm_client

def get_reranker():
    global _reranker
    if _reranker is None:
        from reranker.cross_encoder import CrossEncoderReranker
        _reranker = CrossEncoderReranker()
    return _reranker

def get_retrieval_chain():
    global _chain
    if _chain is None:
        from rag.retrieval_chain import RetrievalChain
        _chain = RetrievalChain(
            retriever=get_retriever(),
            reranker=get_reranker(),
            llm_client=get_llm_client()
        )
    return _chain

def get_tracker():
    global _tracker
    if _tracker is None:
        from analytics.tracker import AnalyticsTracker
        _tracker = AnalyticsTracker()
    return _tracker

def get_evaluator():
    global _evaluator
    if _evaluator is None:
        from evaluation.ragas_evaluator import LocalRagasEvaluator
        client = get_llm_client()
        _evaluator = LocalRagasEvaluator(base_url=client.base_url, model_name=client.model)
    return _evaluator

# --- FastAPI Initialization ---
app = FastAPI(
    title="Medical Research Assistant API",
    description="Backend endpoints for hybrid search, summarization, entity extraction, and local RAGAS evaluation.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
from routes import (
    document_routes,
    query_routes,
    summary_routes,
    entity_routes,
    search_routes,
    analytics_routes,
    evaluation_routes,
)

app.include_router(document_routes.router)
app.include_router(query_routes.router)
app.include_router(summary_routes.router)
app.include_router(entity_routes.router)
app.include_router(search_routes.router)
app.include_router(analytics_routes.router)
app.include_router(evaluation_routes.router)

# Serve Frontend Statically
frontend_dir = os.path.join(os.path.dirname(BASE_DIR), "frontend")

if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{page_name}.html")
    async def read_page(page_name: str):
        page_path = os.path.join(frontend_dir, f"{page_name}.html")
        if os.path.exists(page_path):
            return FileResponse(page_path)
        raise HTTPException(status_code=404, detail="Page not found.")

if __name__ == "__main__":
    import uvicorn
    # Pre-load embedder and store to trigger downloading/loading weights upfront
    print("[INFO] Warm-starting model singletons ...")
    try:
        get_embedder()
        get_faiss_store()
        get_reranker()
        get_llm_client()
    except Exception as e:
        print(f"[WARNING] Lazy warm-start encountered issues: {e}")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
