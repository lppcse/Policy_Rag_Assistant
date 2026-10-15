"""Embedding generation and FAISS vector store management.

Provides batch embedding via OpenAI text-embedding-3-small with L2 normalization,
and a VectorStore class backed by FAISS IndexFlatIP (cosine similarity) with
metadata persistence in the index/ directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Dict, Optional

import faiss
import numpy as np
from openai import OpenAI

from src.config import (
    EMBEDDING_MODEL,
    INDEX_DIR,
    INDEX_FILE,
    METADATA_FILE,
    TOP_K,
    get_openai_api_key,
)


def embed(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    client: Optional[OpenAI] = None,
    batch_size: int = 100,
) -> np.ndarray:
    """Generate L2-normalized float32 embedding vectors for a list of texts.

    Args:
        texts: List of strings to embed.
        model: OpenAI embedding model name.
        client: Optional pre-configured OpenAI client instance.
        batch_size: Number of texts per API request.

    Returns:
        np.ndarray: 2D numpy array of shape (len(texts), embedding_dim), float32,
                    L2-normalized so inner product equals cosine similarity.
    """
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    if client is None:
        client = OpenAI(api_key=get_openai_api_key())

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Replace newlines with spaces as recommended by OpenAI best practices
        cleaned_batch = [t.replace("\n", " ") for t in batch]
        response = client.embeddings.create(input=cleaned_batch, model=model)
        # Preserve original order from response data
        batch_vectors = [item.embedding for item in response.data]
        all_embeddings.extend(batch_vectors)

    vectors = np.array(all_embeddings, dtype=np.float32)

    # Perform L2 normalization for cosine similarity with IndexFlatIP
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.clip(norms, a_min=1e-12, a_max=None)

    return vectors.astype(np.float32)


class VectorStore:
    """FAISS-based vector store using IndexFlatIP for cosine similarity search.

    Maintains vector embeddings alongside document chunk metadata (text, source file, section).
    """

    def __init__(self) -> None:
        self.index: Optional[faiss.IndexFlatIP] = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension: int = 0

    def build(
        self,
        chunks: List[Dict[str, Any]],
        client: Optional[OpenAI] = None,
    ) -> None:
        """Embed text chunks and build the FAISS IndexFlatIP index.

        Args:
            chunks: List of dictionaries with keys 'text', 'source_file', 'section'.
            client: Optional OpenAI client.
        """
        if not chunks:
            raise ValueError("Cannot build index from empty chunk list.")

        texts = [chunk["text"] for chunk in chunks]
        vectors = embed(texts, client=client)

        self.dimension = vectors.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(vectors)
        self.metadata = chunks

    def save(
        self,
        index_path: Path | str = INDEX_FILE,
        metadata_path: Path | str = METADATA_FILE,
    ) -> None:
        """Persist FAISS index and metadata to disk.

        Args:
            index_path: File path to save the FAISS binary index.
            metadata_path: File path to save the JSON metadata.
        """
        if self.index is None:
            raise RuntimeError("Cannot save an uninitialized vector store. Call build() or load() first.")

        idx_path = Path(index_path)
        meta_path = Path(metadata_path)

        idx_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(idx_path))

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def load(
        self,
        index_path: Path | str = INDEX_FILE,
        metadata_path: Path | str = METADATA_FILE,
    ) -> None:
        """Load FAISS index and metadata from disk.

        Args:
            index_path: Path to the serialized FAISS index.
            metadata_path: Path to the metadata JSON file.

        Raises:
            FileNotFoundError: If the index or metadata file does not exist.
        """
        idx_path = Path(index_path)
        meta_path = Path(metadata_path)

        if not idx_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"Vector store index not found at {idx_path} or {meta_path}.\n"
                "Please run ingestion first using:\n"
                "    python src/main.py ingest"
            )

        self.index = faiss.read_index(str(idx_path))
        self.dimension = self.index.d

        with open(meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

    def search(
        self,
        query: str,
        k: int = TOP_K,
        client: Optional[OpenAI] = None,
    ) -> List[Dict[str, Any]]:
        """Perform top-K cosine similarity search for a query string.

        Args:
            query: The query text to search for.
            k: Number of nearest neighbors to retrieve.
            client: Optional OpenAI client.

        Returns:
            List of dictionaries containing matched chunk data plus similarity 'score'.
        """
        if self.index is None:
            raise RuntimeError("Vector store index is not loaded. Call load() or build() first.")

        if self.index.ntotal == 0:
            return []

        # Vectorize and normalize the query
        query_vec = embed([query], client=client)
        actual_k = min(k, self.index.ntotal)

        distances, indices = self.index.search(query_vec, actual_k)

        results: List[Dict[str, Any]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            chunk = dict(self.metadata[idx])
            chunk["score"] = float(dist)
            results.append(chunk)

        return results
