"""Services module for IterateSwarm AI.

This module provides services for:
- Vector embeddings (Ollama)
- Vector storage and similarity search (Qdrant)
"""

from src.services.qdrant import QdrantService, get_qdrant_service
from src.services.embeddings import (
    OllamaEmbeddings,
    EmbeddingResult,
    SimilarityResult,
    get_embeddings_service,
)

__all__ = [
    "QdrantService",
    "get_qdrant_service",
    "OllamaEmbeddings",
    "EmbeddingResult",
    "SimilarityResult",
    "get_embeddings_service",
]
