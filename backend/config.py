"""
Medical-RAG — Backend Centralized Configuration
===============================================
Centralized settings for directory paths, thresholds, and model settings.
"""

import os
import torch

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data")
INDEX_DIR = os.path.join(BASE_DIR, "faiss_index")
ANALYTICS_FILE = os.path.join(BASE_DIR, "analytics", "data.json")
EVALUATION_FILE = os.path.join(BASE_DIR, "evaluation", "history.json")
METADATA_FILE = os.path.join(BASE_DIR, "vectorstore", "metadata.json")

# Ensure necessary directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "analytics"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "evaluation"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "vectorstore"), exist_ok=True)

# ── Device ────────────────────────────────────────────────────────────────────
DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

# ── Embedding Model ──────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"

# ── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = 600
CHUNK_OVERLAP: int = 150

# ── Retrieval ────────────────────────────────────────────────────────────────
RETRIEVAL_K: int = 10          # Final docs returned by MMR
RETRIEVAL_FETCH_K: int = 30    # Candidates fetched before MMR diversity filter
RERANK_FETCH_K: int = 20       # Candidates sent to cross-encoder
RERANK_TOP_K: int = 5          # Final docs after re-ranking

# ── Similarity Threshold (hallucination prevention) ──────────────────────────
SIMILARITY_THRESHOLD: float = 0.60

INSUFFICIENT_INFO_MSG: str = (
    "The uploaded documents do not contain enough information "
    "to answer this question."
)

# ── Cross-Encoder Re-Ranker ──────────────────────────────────────────────────
CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ── LLM (Ollama) ─────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_PRIMARY_MODEL: str = "qwen3:14b"
OLLAMA_FALLBACK_MODEL: str = "qwen3:8b"
OLLAMA_TIMEOUT: int = 120          # seconds per request
OLLAMA_STREAM: bool = True         # enable streaming by default
CONVERSATION_HISTORY_LIMIT: int = 10  # max turns to keep in memory

# ── System Prompts ───────────────────────────────────────────────────────────
SYSTEM_PROMPT: str = """You are a medical literature assistant.

Rules:

1. Answer ONLY using retrieved context.
2. Never use outside knowledge.
3. If context is insufficient, say:
   "The uploaded documents do not contain enough information to answer this question."
4. Cite source filenames.
5. Do not guess.
6. Do not provide medical advice.
7. If information is unavailable in the uploaded documents, explicitly state that."""

OLLAMA_SYSTEM_PROMPT: str = """You are a medical literature assistant.

Rules:

1. Answer ONLY from retrieved context.
2. Never use outside knowledge.
3. Never guess.
4. If context is insufficient, say:
   "The uploaded documents do not contain enough information to answer this question."
5. Cite filenames and page numbers.
6. Do not provide medical advice.
7. Summarize evidence from multiple sources when available.
8. Return structured output in this EXACT format:

Answer:
<your answer here>

Sources:
* <filename.pdf> (page <X>)
* <filename.pdf> (page <Y>)

Confidence:
<0.00-1.00>"""

OLLAMA_FALLBACK_SYSTEM_PROMPT: str = """You are a medical assistant.

Rules:

1. Answer using your general pre-trained medical knowledge since no relevant uploaded documents were found.
2. Keep your response concise, professional, and accurate.
3. Never guess or fabricate information.
4. Do not provide medical advice.
5. Begin your answer with the disclaimer: "[WARNING: General Knowledge Fallback - Not verified by uploaded documents]" and do NOT include any 'Sources' list."""

DEFAULT_FALLBACK_ENABLED: bool = True
