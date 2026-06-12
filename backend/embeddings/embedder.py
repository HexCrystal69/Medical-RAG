"""
Embedder Module
---------------
Wraps the BAAI/bge-large-en-v1.5 sentence-transformer model
into a LangChain-compatible embedding interface.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from config import DEVICE, EMBEDDING_MODEL


class Embedder:
    """Provides a LangChain-compatible embedding model."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        device: str = DEVICE,
        normalize_embeddings: bool = True,
    ) -> None:
        self.model_name = model_name
        self.model_kwargs = {"device": device}
        self.encode_kwargs = {"normalize_embeddings": normalize_embeddings}

        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs=self.model_kwargs,
            encode_kwargs=self.encode_kwargs,
        )
        print(f"[INFO] Embedding model loaded: {self.model_name} (device={device})")

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """Return the underlying LangChain embedding object."""
        return self.embeddings
