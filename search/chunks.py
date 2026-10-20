"""Chunk vector search over the AWMF corpus.

Embeds a query with the Qwen3-Embedding instruct prefix (via the CPU sidecar
`settings.embedding_url`, default :8081), slices to 2048 + L2-normalizes (matching
the indexed document vectors), then returns HNSW cosine top-k from the `chunks`
table.

This mirrors the Leitlinien KB query convention exactly — the indexed vectors used
the same model/quant/flags and the same slice→normalize order, so query vectors are
directly comparable.

Errors mirror the existing search/hybrid.py pattern: the endpoint returns 503 when
the embedding sidecar is unavailable and 500 for other embedding failures.

Fallback: in embed mode, an unavailable embedding sidecar (``EmbeddingError``) is
caught and degrades to the keyword (tsvector) search instead of raising 503. That
fallback is only meaningful where ``chunks.search_vector`` is populated; on a host
where it is NULL, run once::

    UPDATE chunks SET search_vector = to_tsvector('german', text) WHERE search_vector IS NULL;
    CREATE INDEX idx_chunks_fts ON chunks USING GIN(search_vector);
"""

import logging
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.config import settings

logger = logging.getLogger(__name__)

STORE_DIM = 2048
INSTRUCT_PREFIX = (
    "Instruct: Given a German medical guideline query, retrieve relevant "
    "guideline passages that answer the query\nQuery: "
)


class EmbeddingError(Exception):
    """Base exception for embedding errors."""

    pass


class LlamaserverConnectionError(EmbeddingError):
    """Raised when the embedding server is unreachable."""

    pass


def embed_query(query: str, url: Optional[str] = None, api_key: Optional[str] = None) -> list[float]:
    """Embed a query with the instruct prefix, slice to 2048, L2-normalize.

    This is the query-side twin of the corpus embedding (which stored raw doc text,
    sliced to 2048, L2-normalized). The instruct prefix is applied on queries only —
    same convention as the Leitlinien KB.
    """
    if not query or not query.strip():
        raise EmbeddingError("Empty query provided for embedding")

    base = url or settings.embedding_url
    key = api_key or getattr(settings, "llamaserver_api_key", "") or ""

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    payload = {"input": [INSTRUCT_PREFIX + query], "model": "qwen3emb8b"}

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{base}/v1/embeddings", json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.ConnectError as e:
        raise LlamaserverConnectionError(f"Cannot connect to embedding server at {base}: {e}")
    except httpx.TimeoutException as e:
        raise LlamaserverConnectionError(f"Embedding request timed out: {e}")
    except httpx.HTTPStatusError as e:
        raise LlamaserverConnectionError(
            f"Embedding server returned error {e.response.status_code}: {e}"
        )

    try:
        embedding = resp.json()["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as e:
        raise EmbeddingError(f"Invalid embedding response from server: {e}")

    # MRL: slice THEN normalize (identical to corpus embed pipeline — order matters)
    vec = embedding[:STORE_DIM]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec]


def _embedding_str(vec: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


def _keyword_search_chunks(
    query: str,
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, object]:
    """Full-text (tsvector) chunk matching — no embeddings, no sidecar.

    For hosts without the embed sidecar (CHUNK_SEARCH_MODE=keyword, e.g. the
    VPS). Requires chunks.search_vector to be populated + GIN-indexed (one-time
    COPY + CREATE INDEX, see the host deploy notes). Item shape matches
    the vector path exactly so endpoints/RAG/UI need no mode awareness.
    """
    where = """
        FROM chunks c
        CROSS JOIN websearch_to_tsquery('german', :query) q
        WHERE c.source_type = 'awmf' AND c.search_vector @@ q
    """
    sql = f"""
        SELECT
            c.id,
            c.source_type,
            c.source_path,
            c.title,
            c.awmf,
            c.society,
            c.page,
            c.seq,
            c.text,
            c.source_id AS document_id,
            ts_rank(c.search_vector, q) AS score
        {where}
        ORDER BY score DESC
        LIMIT :limit OFFSET :offset
    """
    count_sql = f"SELECT count(*) {where}"

    params: dict[str, object] = {"query": query, "limit": limit, "offset": offset}
    results = db.execute(text(sql), params).fetchall()
    total = db.execute(text(count_sql), {"query": query}).scalar_one()

    if total == 0:
        logger.info(
            "chunk keyword search returned 0 results for %r — chunks.search_vector "
            "may be unpopulated on this host (see module docstring)",
            query,
        )

    items = [
        {
            "id": row.id,
            "source_type": row.source_type,
            "source_path": row.source_path,
            "title": row.title,
            "awmf": row.awmf,
            "society": row.society,
            "page": row.page,
            "seq": row.seq,
            "text": row.text,
            "document_id": row.document_id,
            "score": float(row.score),
        }
        for row in results
    ]
    return {
        "items": items,
        "total": int(total),
        "query": query,
        "limit": limit,
        "offset": offset,
    }


def search_chunks(
    query: str,
    db: Session,
    limit: int = 20,
    offset: int = 0,
    llamaserver_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict[str, object]:
    """HNSW cosine top-k over chunk embeddings. Returns dict with items/total."""
    if not query or not query.strip():
        return {"items": [], "total": 0, "query": query, "limit": limit, "offset": offset}
    if settings.chunk_search_mode == "keyword":
        return _keyword_search_chunks(query, db, limit, offset)

    try:
        embedding = embed_query(query, llamaserver_url, api_key)
    except EmbeddingError:
        logger.warning("embedding sidecar unavailable — falling back to keyword chunk search")
        return _keyword_search_chunks(query, db, limit, offset)
    embedding_str = _embedding_str(embedding)

    # HNSW cosine distance (<->); score = 1 - distance, so higher = more similar.
    # ORDER BY distance ASC == most similar first. `total` = number of returned rows
    # (hard-capped at `limit`); there is no relevance threshold, so a full-corpus count
    # would be misleading (594k ≠ matches). Matches the 'limit to 20 total' requirement.
    sql = """
        SELECT
            c.id,
            c.source_type,
            c.source_path,
            c.title,
            c.awmf,
            c.society,
            c.page,
            c.seq,
            c.text,
            c.source_id AS document_id,
            1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
        FROM chunks c
        WHERE c.source_type = 'awmf'
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :limit OFFSET :offset
    """

    params = {
        "embedding": embedding_str,
        "limit": limit,
        "offset": offset,
    }

    results = db.execute(text(sql), params).fetchall()
    total = len(results)

    items = []
    for row in results:
        items.append(
            {
                "id": row.id,
                "source_type": row.source_type,
                "source_path": row.source_path,
                "title": row.title,
                "awmf": row.awmf,
                "society": row.society,
                "page": row.page,
                "seq": row.seq,
                "text": row.text,
                "document_id": row.document_id,
                "score": float(row.score),
            }
        )

    return {
        "items": items,
        "total": int(total),
        "query": query,
        "limit": limit,
        "offset": offset,
    }
