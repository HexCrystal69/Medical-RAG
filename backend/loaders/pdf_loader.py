"""
PDF Loader Module
-----------------
Loads PDF files, extracts text, and returns LangChain Document objects
split into chunks for downstream embedding and retrieval.
"""

from __future__ import annotations

import os
import re
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import CHUNK_SIZE, CHUNK_OVERLAP

_DISEASE_KEYWORDS: dict[str, str] = {
    "diabetes": "diabetes",
    "coronary": "coronary_artery_disease",
    "heart": "heart_disease",
    "cardiac": "cardiac",
    "asthma": "asthma",
    "copd": "copd",
    "gina": "asthma",
    "alzheimer": "alzheimers",
    "dementia": "dementia",
    "hypertension": "hypertension",
    "stroke": "stroke",
    "cancer": "cancer",
    "oncology": "oncology",
    "tuberculosis": "tuberculosis",
    "hepatitis": "hepatitis",
    "respiratory": "respiratory",
    "pulmonary": "pulmonary",
    "renal": "renal",
    "kidney": "kidney",
    "liver": "liver",
}


def _infer_disease_category(filename: str) -> str:
    """Derive a disease category from the PDF filename."""
    name_lower = filename.lower()
    for keyword, category in _DISEASE_KEYWORDS.items():
        if keyword in name_lower:
            return category
    return "general"


class PDFLoader:
    """Loads and chunks PDF documents for RAG pipelines."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def load_single_pdf(self, file_path: str) -> List[Document]:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        if not file_path.lower().endswith(".pdf"):
            raise ValueError(f"Expected a .pdf file, got: {file_path}")

        loader = PyPDFLoader(file_path)
        raw_documents = loader.load()

        basename = os.path.basename(file_path)
        disease_category = _infer_disease_category(basename)

        # Enrich metadata
        for doc in raw_documents:
            doc.metadata["source"] = basename
            doc.metadata["filename"] = basename
            doc.metadata["page_number"] = doc.metadata.get("page", 0) + 1  # 1-indexed
            doc.metadata["disease_category"] = disease_category

        chunks = self.text_splitter.split_documents(raw_documents)
        return chunks

    def load_directory(self, directory_path: str) -> List[Document]:
        if not os.path.isdir(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        all_documents: List[Document] = []
        pdf_files = sorted(
            f for f in os.listdir(directory_path) if f.lower().endswith(".pdf")
        )

        if not pdf_files:
            print(f"[WARNING] No PDF files found in: {directory_path}")
            return all_documents

        for filename in pdf_files:
            file_path = os.path.join(directory_path, filename)
            print(f"[INFO] Loading: {filename}")
            docs = self.load_single_pdf(file_path)
            all_documents.extend(docs)
            print(f"  -> {len(docs)} chunks extracted")

        print(f"\n[INFO] Total documents loaded: {len(all_documents)} chunks from {len(pdf_files)} PDF(s)")
        return all_documents
