"""
FastAPI Routes — PDF Management
================================
Supports PDF uploading, listing, deletion, incremental FAISS indexing,
and manual database rebuilding.
"""

import os
import time
import json
import uuid
import shutil
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
import pypdf

from config import UPLOAD_DIR, METADATA_FILE
from loaders.pdf_loader import PDFLoader

router = APIRouter(prefix="/documents", tags=["Documents"])

def _read_metadata() -> Dict[str, Any]:
    if not os.path.exists(METADATA_FILE):
        return {}
    try:
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_metadata(data: Dict[str, Any]) -> None:
    try:
        with open(METADATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as exc:
        print(f"[ERROR] Failed to save metadata: {exc}")

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a medical PDF, parse chunks, and incrementally add them to FAISS."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = str(uuid.uuid4())
    filename = file.filename
    save_path = os.path.join(UPLOAD_DIR, filename)

    # Save to disk
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save PDF to disk: {exc}")

    # Extract page count
    try:
        reader = pypdf.PdfReader(save_path)
        page_count = len(reader.pages)
    except Exception as exc:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=400, detail=f"Failed to read PDF structure: {exc}")

    # Generate chunks
    from main import get_embedder, get_faiss_store, get_retriever
    try:
        loader = PDFLoader()
        chunks = loader.load_single_pdf(save_path)
    except Exception as exc:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Failed to parse and chunk PDF: {exc}")

    if not chunks:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=400, detail="The PDF did not contain readable text chunks.")

    # Generate unique chunk IDs
    chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]

    # Add incrementally to FAISS store
    try:
        faiss_store = get_faiss_store()
        faiss_store.add_documents(chunks, ids=chunk_ids)
        faiss_store.save_index()
    except Exception as exc:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Failed to index documents in vector database: {exc}")

    # Log document in metadata JSON
    metadata = _read_metadata()
    metadata[doc_id] = {
        "id": doc_id,
        "filename": filename,
        "page_count": page_count,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_ids": chunk_ids
    }
    _write_metadata(metadata)

    # Update dynamic BM25 search corpus
    try:
        retriever = get_retriever()
        # Retrieve all chunks currently in index
        all_chunks = []
        if faiss_store.vectorstore is not None:
            # We can extract all documents from FAISS store directly
            all_chunks = list(faiss_store.vectorstore.docstore._dict.values())
        retriever.update_documents(all_chunks)
    except Exception as exc:
        print(f"[WARNING] Failed to update BM25 corpus: {exc}")

    return {
        "message": f"Successfully uploaded and indexed {filename}",
        "document": {
            "id": doc_id,
            "filename": filename,
            "page_count": page_count,
            "timestamp": metadata[doc_id]["timestamp"]
        }
    }

@router.get("")
async def get_documents():
    """Retrieve the list of all uploaded and indexed medical PDFs."""
    metadata = _read_metadata()
    return list(metadata.values())

@router.delete("/{id}")
async def delete_document(id: str):
    """Delete a medical PDF, its source file, and purge its chunks from FAISS."""
    metadata = _read_metadata()
    if id not in metadata:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_info = metadata[id]
    filename = doc_info["filename"]
    chunk_ids = doc_info["chunk_ids"]
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 1. Delete source file
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as exc:
            print(f"[WARNING] Failed to delete file {file_path}: {exc}")

    # 2. Delete from FAISS vector store
    from main import get_faiss_store, get_retriever
    try:
        faiss_store = get_faiss_store()
        faiss_store.delete_documents(chunk_ids)
        faiss_store.save_index()
    except Exception as exc:
        print(f"[WARNING] Failed to remove chunks from FAISS: {exc}")

    # 3. Remove entry from metadata
    del metadata[id]
    _write_metadata(metadata)

    # 4. Update dynamic BM25 corpus
    try:
        retriever = get_retriever()
        all_chunks = []
        if faiss_store.vectorstore is not None:
            all_chunks = list(faiss_store.vectorstore.docstore._dict.values())
        retriever.update_documents(all_chunks)
    except Exception as exc:
        print(f"[WARNING] Failed to update BM25 corpus: {exc}")

    return {"message": f"Successfully deleted document {filename}"}

@router.post("/rebuild-index")
async def rebuild_index():
    """Wipe the current FAISS store and perform a full rebuild of all files in UPLOAD_DIR."""
    metadata = _read_metadata()
    pdf_loader = PDFLoader()

    # Load all chunks across all PDFs in the directory
    try:
        all_chunks = pdf_loader.load_directory(UPLOAD_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load documents from data directory: {exc}")

    from main import get_faiss_store, get_retriever
    faiss_store = get_faiss_store()

    if not all_chunks:
        # Wipe vector store and metadata completely
        faiss_store.vectorstore = None
        # Attempt to remove index folder
        if os.path.exists(faiss_store.index_dir):
            try:
                shutil.rmtree(faiss_store.index_dir)
                os.makedirs(faiss_store.index_dir, exist_ok=True)
            except Exception:
                pass
        _write_metadata({})
        retriever = get_retriever()
        retriever.update_documents([])
        return {"message": "All database indexes wiped successfully. (Directory was empty)"}

    # Re-generate IDs for all documents
    new_metadata = {}
    new_chunk_ids = []
    
    # Process files one by one to reconstruct correct page counts and mappings
    pdf_files = sorted(f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(".pdf"))
    
    # We rebuild FAISS with a clean set of chunks
    faiss_store.vectorstore = None
    
    for filename in pdf_files:
        doc_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        try:
            reader = pypdf.PdfReader(file_path)
            page_count = len(reader.pages)
            file_chunks = pdf_loader.load_single_pdf(file_path)
        except Exception:
            continue
            
        file_chunk_ids = [f"{doc_id}_{i}" for i in range(len(file_chunks))]
        new_chunk_ids.extend(file_chunk_ids)
        
        new_metadata[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "page_count": page_count,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "chunk_ids": file_chunk_ids
        }

    # Rebuild index
    try:
        faiss_store.build_index(all_chunks, ids=new_chunk_ids)
        faiss_store.save_index()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to construct index: {exc}")

    _write_metadata(new_metadata)

    # Update retriever
    try:
        retriever = get_retriever()
        retriever.update_documents(all_chunks)
    except Exception as exc:
        print(f"[WARNING] Failed to update BM25: {exc}")

    return {"message": f"Successfully rebuilt index across {len(pdf_files)} PDF(s)"}
