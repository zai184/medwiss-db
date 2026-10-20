"""Embedding generation using local llamaserver API.

This module provides embedding generation for medical content using a local
llamaserver instance. Embeddings are cached to avoid redundant API calls.

NO Cloud APIs - all embeddings generated locally via llamaserver.
"""

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
import numpy as np

from api.config import settings

logger = logging.getLogger(__name__)

# Default embedding dimension (1536 for most text embedding models)
EMBEDDING_DIMENSION = 1536


class EmbeddingError(Exception):
    """Base exception for embedding errors."""

    pass


class LlamaserverConnectionError(EmbeddingError):
    """Raised when llamaserver is unreachable."""

    pass


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding generation fails."""

    pass


def _get_cache_path() -> Path:
    """Get the cache directory for embeddings."""
    cache_dir = Path(__file__).parent.parent / ".cache" / "embeddings"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _compute_text_hash(text: str) -> str:
    """Compute hash for text to use as cache key."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cached_embedding(text_hash: str) -> Optional[list[float]]:
    """Load embedding from disk cache if it exists."""
    cache_file = _get_cache_path() / f"{text_hash}.npy"
    if cache_file.exists():
        try:
            embedding = np.load(cache_file).tolist()
            logger.debug(f"Loaded cached embedding for hash {text_hash[:8]}...")
            return embedding
        except Exception as e:
            logger.warning(f"Failed to load cached embedding: {e}")
            return None
    return None


def _save_cached_embedding(text_hash: str, embedding: list[float]) -> None:
    """Save embedding to disk cache."""
    cache_file = _get_cache_path() / f"{text_hash}.npy"
    try:
        np.save(cache_file, np.array(embedding))
        logger.debug(f"Saved embedding cache for hash {text_hash[:8]}...")
    except Exception as e:
        logger.warning(f"Failed to save embedding cache: {e}")


@lru_cache(maxsize=1000)
def _generate_embedding_cached(text: str, llamaserver_url: str) -> list[float]:
    """Generate embedding with LRU memory cache.

    This function is cached in memory to avoid redundant calls for
    the same text within the same process lifetime.
    """
    return _generate_embedding_impl(text, llamaserver_url)


def _generate_embedding_impl(text: str, llamaserver_url: str) -> list[float]:
    """Core implementation of embedding generation via llamaserver.

    Args:
        text: Text to generate embedding for.
        llamaserver_url: URL of the llamaserver instance.

    Returns:
        List of float values representing the embedding vector.

    Raises:
        LlamaserverConnectionError: If llamaserver is unreachable.
        EmbeddingGenerationError: If embedding generation fails.
    """
    if not text or not text.strip():
        raise EmbeddingError("Empty text provided for embedding generation")

    # Check disk cache first
    text_hash = _compute_text_hash(text)
    cached = _load_cached_embedding(text_hash)
    if cached is not None:
        return cached

    # Prepare request for llamaserver embeddings endpoint
    headers = {"Content-Type": "application/json"}
    if settings.llamaserver_api_key:
        headers["Authorization"] = f"Bearer {settings.llamaserver_api_key}"

    # llamaserver uses OpenAI-compatible embeddings API format
    payload = {
        "input": text[:8192],  # Limit text length to avoid token limits
        "model": "text-embedding",  # Model name used by llamaserver
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{llamaserver_url}/v1/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.ConnectError as e:
        raise LlamaserverConnectionError(f"Cannot connect to llamaserver at {llamaserver_url}: {e}")
    except httpx.TimeoutException as e:
        raise LlamaserverConnectionError(f"Request to llamaserver timed out: {e}")
    except httpx.HTTPStatusError as e:
        raise LlamaserverConnectionError(
            f"llamaserver returned error {e.response.status_code}: {e}"
        )

    # Extract embedding from response
    try:
        result = response.json()
        embedding = result["data"][0]["embedding"]

        # Validate embedding dimension
        if len(embedding) != EMBEDDING_DIMENSION:
            logger.warning(
                f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSION}"
            )

    except (KeyError, IndexError) as e:
        raise EmbeddingGenerationError(f"Invalid response format from llamaserver: {e}")

    # Save to disk cache
    _save_cached_embedding(text_hash, embedding)

    return embedding


def generate_embedding(
    text: str,
    llamaserver_url: Optional[str] = None,
    use_cache: bool = True,
) -> list[float]:
    """Generate embedding for text using local llamaserver.

    Uses a two-level caching system:
    1. LRU in-memory cache for frequently accessed texts within the same process
    2. Disk cache (numpy files) for persistence across process restarts

    Args:
        text: Text to generate embedding for.
        llamaserver_url: Override for llamaserver URL (default: from settings).
        use_cache: Whether to use caching (default: True).

    Returns:
        List of float values (1536 dimensions) representing the embedding vector.

    Raises:
        EmbeddingError: If text is empty.
        LlamaserverConnectionError: If llamaserver is unreachable.
        EmbeddingGenerationError: If embedding generation fails.

    Example:
        >>> embedding = generate_embedding("Medical case description...")
        >>> len(embedding)
        1536
    """
    url = llamaserver_url or settings.llamaserver_url

    if not use_cache:
        return _generate_embedding_impl(text, url)

    return _generate_embedding_cached(text, url)


async def generate_embedding_async(
    text: str,
    llamaserver_url: Optional[str] = None,
) -> list[float]:
    """Async version of generate_embedding.

    Args:
        text: Text to generate embedding for.
        llamaserver_url: Override for llamaserver URL (default: from settings).

    Returns:
        List of float values (1536 dimensions) representing the embedding vector.

    Raises:
        EmbeddingError: If text is empty.
        LlamaserverConnectionError: If llamaserver is unreachable.
        EmbeddingGenerationError: If embedding generation fails.
    """
    if not text or not text.strip():
        raise EmbeddingError("Empty text provided for embedding generation")

    url = llamaserver_url or settings.llamaserver_url

    # Check disk cache first
    text_hash = _compute_text_hash(text)
    cached = _load_cached_embedding(text_hash)
    if cached is not None:
        return cached

    headers = {"Content-Type": "application/json"}
    if settings.llamaserver_api_key:
        headers["Authorization"] = f"Bearer {settings.llamaserver_api_key}"

    payload = {
        "input": text[:8192],
        "model": "text-embedding",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/v1/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.ConnectError as e:
        raise LlamaserverConnectionError(f"Cannot connect to llamaserver at {url}: {e}")
    except httpx.TimeoutException as e:
        raise LlamaserverConnectionError(f"Request to llamaserver timed out: {e}")
    except httpx.HTTPStatusError as e:
        raise LlamaserverConnectionError(
            f"llamaserver returned error {e.response.status_code}: {e}"
        )

    try:
        result = response.json()
        embedding = result["data"][0]["embedding"]
    except (KeyError, IndexError) as e:
        raise EmbeddingGenerationError(f"Invalid response format from llamaserver: {e}")

    _save_cached_embedding(text_hash, embedding)

    return embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity value between -1 and 1.
    """
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
