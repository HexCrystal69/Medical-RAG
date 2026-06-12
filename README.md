# 🩺 Full Stack Medical Research Assistant

A local full-stack medical research assistant combining semantic vector search and keyword queries with Ollama Qwen3 to answer clinical literature questions with cited references.

---

## 🏗️ System Architecture

```
                       +----------------------------------+
                       |       Web Client (HTML/JS)       |
                       +-----------------+----------------+
                                         |
                                         | REST Requests / JSON
                                         v
                       +----------------------------------+
                       |          FastAPI Server          |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |      Hybrid Retriever Gate       |
                       |    - BM25 Keyword Matching       |
                       |    - FAISS Vector Embedding      |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |  Reciprocal Rank Fusion (RRF)    |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |  Cross-Encoder Rescoring (Top-5) |
                       +-----------------+----------------+
                                         |
                                         v
                       +----------------------------------+
                       |    Local LLM (Ollama Qwen3)      |
                       +----------------------------------+
```

---

## 🛠️ Technology Stack

- **Frontend UI:** Plain HTML5, CSS3 (Glassmorphism layout, transitions), JavaScript (HTML5 Canvas simulation for force-directed knowledge graph, Chart.js CDN for metrics visualization).
- **Backend API:** FastAPI, Uvicorn, Python 3.10.
- **Vector Index:** FAISS, LangChain.
- **Embedding Model:** `BAAI/bge-large-en-v1.5` (GPU/CUDA accelerated).
- **Re-ranking Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **Inference Model:** Qwen3 via Ollama (configured with automatic general pre-trained fallback).

---

## 📂 Project Structure

```
backend/
├── main.py                 # FastAPI Web Server entrypoint
├── config.py               # Path configurations and prompts
├── requirements.txt        # Server Python dependencies
├── Dockerfile              # Container building instruction
├── routes/                 # REST API endpoints
│   ├── document_routes.py  # PDF indexing, listing, delete
│   ├── query_routes.py     # RAG queries & citations
│   ├── summary_routes.py   # Research summary builder
│   ├── entity_routes.py    # Clinical NLP entities
│   ├── search_routes.py    # Direct search matching
│   ├── analytics_routes.py # Stats aggregator
│   └── evaluation_routes.py# Benchmark & quality checks
├── retriever/
│   └── hybrid_retriever.py # RRF vector + keyword fusion
├── embeddings/
│   └── embedder.py         # Embedding model wrapper
├── vectorstore/
│   └── faiss_store.py      # FAISS DB manager
├── llm/
│   └── qwen_client.py      # Ollama client
├── evaluation/
│   └── ragas_evaluator.py  # Quality metrics evaluator
├── analytics/
│   └── tracker.py          # Metrics logging manager
├── utils/
│   └── exporter.py         # Report generation (TXT/PDF)
└── tests/
    └── test_backend.py     # Unit verification tests

frontend/
├── index.html              # Landing dashboard & files upload
├── chat.html               # Chat interface with citations
├── summary.html            # Research summarizer UI
├── search.html             # Passage verification search
├── analytics.html          # Performance charts
├── evaluation.html         # Quality metrics dashboard
├── graph.html              # Force-directed knowledge graph
├── about.html              # Architecture details page
├── css/
│   └── style.css           # Premium styling sheet
└── js/                     # JS controllers
    ├── app.js, chat.js, summary.js, search.js, analytics.js, evaluation.js, graph.js
```

---

## 🚀 Installation & Launch

### 1. Prerequisite: Setup Ollama
Download and run Ollama on your machine.
Pull the Qwen model:
```bash
ollama pull qwen3:8b
```

### 2. Standalone Local Install
Clone the repository, navigate to the folder, and run:
```bash
# Install Python libraries
pip install -r backend/requirements.txt

# Launch FastAPI web server
python backend/main.py
```
Open `http://localhost:8000` in your web browser.

### 3. Docker Compose Launch
Run from the root directory to spin up the container:
```bash
docker compose up --build
```
The Docker container will automatically expose port `8000` and map queries to your host's local Ollama endpoint.

---

## 🔍 REST API Documentation

### Document Catalog
- `POST /documents/upload` - Upload a medical PDF and incrementally insert it to the database index.
- `GET /documents` - Returns catalog listings (filenames, page count, timestamp).
- `DELETE /documents/{id}` - Deletes PDF and purges its chunk IDs from the FAISS database.
- `POST /documents/rebuild-index` - Force rebuild of vector tables from scratch.

### RAG Pipeline
- `POST /query` - Executes query matching (Vector, BM25, or Hybrid via RRF) and returns answers and references.
- `POST /query/export` - Export specific answers to TXT/PDF.

### Clinical NLP & Graphs
- `POST /summary` - Generates a 6-part clinical topic summary.
- `POST /entities` - Extracts structured medical terms.
- `POST /search` - Returns matches directly from vector stores without LLM generation.

### Quality & Diagnostics
- `GET /analytics` - Fetches latencies and reference rates.
- `POST /evaluate/generate-questions` - Formulates test sets from index chunks.
- `POST /evaluate/run` - Runs quality metrics checks on test set queries.

---

## Screenshot

<img width="1919" height="998" alt="Screenshot 2026-06-12 181535" src="https://github.com/user-attachments/assets/f0d812a5-0674-4de4-9e57-39e2dd36553d" />

## 🧪 Running Automated Tests

To execute the unit tests and verify hybrid retriever ranking, threshold gates, and mocks:
```bash
python backend/tests/test_backend.py
```
