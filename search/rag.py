"""RAG over AWMF guideline chunks.

Retrieves top-k chunks with `search_chunks`, builds a German prompt with the
retrieved passages (numbered, with source metadata), and calls an OpenAI-compatible
chat endpoint to produce an answer with explicit source pointers. Primary: the 9B
(Qwen3.5-9B-Instruct on :8080). Fallback: DeepSeek cloud API when DEEPSEEK_API_KEY
is set (e.g. on the VPS, where no GPU llama-server runs).

Deliberately simple: retrieval stays in `search_chunks` (single source of truth
for the query embedding + exact cosine scan); this module only adds the prompt
and the chat call. No persistence, no conversation history — one-shot per query.
"""

import logging
from typing import Optional, cast

import httpx
from sqlalchemy.orm import Session

from api.config import settings
from search.chunks import search_chunks

logger = logging.getLogger(__name__)

TOP_K = 6  # passages fed to the model; enough to answer, small enough for the 9B context window


class RagError(Exception):
    """Base exception for RAG errors."""


class RagLlamaserverError(RagError):
    """Raised when the 9B chat server is unreachable or errors."""


SYSTEM_PROMPT = (
    "Du bist ein deutschsprachiger medizinischer Assistent, der ausschließlich anhand "
    "der bereitgestellten Leitlinien-Passagen antwortet. "
    "WICHTIG: Schreibe deine gesamte Antwort auf Deutsch, auch wenn die Frage oder die "
    "Passagen englische Begriffe enthalten — übersetze diese. "
    "Antworte präzise und mit Quellenangabe: zitiere Quellen als [Quelle N] und nenne "
    "die Leitlinien-Kennung (z. B. 053-012) sowie die Seitenzahl. "
    "Wenn die Passagen die Frage nicht beantworten können, sage das deutlich und rate nicht."
)


def _build_prompt(query: str, items: list[dict[str, object]]) -> str:
    """Build the user prompt from retrieved chunks."""
    passages = []
    for i, item in enumerate(items, start=1):
        src = item.get("awmf") or item.get("title") or "unbekannt"
        page = item.get("page")
        page_s = f", Seite {page}" if page is not None else ""
        # Truncate each passage to keep the total prompt bounded (9B context is ~8k tokens).
        text = (item.get("text") or "").strip()
        if len(text) > 1200:
            text = text[:1200] + " […]"
        passages.append(f"[Quelle {i}] {src}{page_s}:\n{text}")

    body = "\n\n".join(passages)
    return (
        f"Frage: {query}\n\n"
        f"Relevante Leitlinien-Passagen:\n{body}\n\n"
        "Beantworte die Frage anhand dieser Passagen. Gib eine klare Antwort und "
        "weise dabei auf die genutzten Quellen hin (Format [Quelle N], Kennung, Seite)."
    )


def _chat(
    messages: list[dict[str, str]],
    llamaserver_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> tuple[str, str]:
    """Run one chat completion: primary llamaserver (9B), fallback OpenRouter.

    Fallback model: DeepSeek V4 Flash via OpenRouter
    (deepseek/deepseek-v4-flash). Returns (content, model_id). Connect/timeout
    failures move down the chain; HTTP error statuses and malformed responses
    raise immediately.
    """
    attempts: list[tuple[str, str, Optional[str]]] = [
        (
            f"{(llamaserver_url or settings.llamaserver_url).rstrip('/')}/v1/chat/completions",
            settings.llamaserver_model,
            api_key if api_key is not None else settings.llamaserver_api_key,
        )
    ]
    if settings.openrouter_api_key:
        attempts.append(
            (
                "https://openrouter.ai/api/v1/chat/completions",
                settings.openrouter_fallback_model,
                settings.openrouter_api_key,
            )
        )

    last_error: Optional[str] = None
    for url, model_id, key in attempts:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = f"Cannot reach chat server at {url}: {e}"
            logger.warning(f"{last_error}; trying next provider")
            continue
        except httpx.HTTPStatusError as e:
            raise RagLlamaserverError(f"Chat server returned error {e.response.status_code}: {e}")

        try:
            return resp.json()["choices"][0]["message"]["content"], model_id
        except (KeyError, IndexError, TypeError) as e:
            raise RagError(f"Invalid chat response: {e}")

    raise RagLlamaserverError(last_error or "No chat server configured")


def answer_rag(
    query: str,
    db: Session,
    top_k: int = TOP_K,
    llamaserver_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict[str, object]:
    """Answer a query over the AWMF corpus with source pointers.

    Retrieves top-k chunks (reusing `search_chunks`), builds a German prompt, and
    calls the 9B chat endpoint. Returns the answer plus the retrieved sources.

    Raises:
        RagError: empty query or invalid chat response.
        RagLlamaserverError: 9B unreachable or returned an error status.
    """
    if not query or not query.strip():
        raise RagError("Empty query provided for RAG")

    # Retrieve. `search_chunks` embeds + exact-scans; reuse it so RAG and the plain
    # search endpoint agree on retrieval semantics. top_k == limit, offset 0.
    result = search_chunks(query, db, limit=top_k, offset=0)
    items = cast(list[dict[str, object]], result.get("items", []))
    if not items:
        return {"answer": "", "sources": [], "query": query, "model": settings.llamaserver_model}

    prompt = _build_prompt(query, items)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    answer, model_used = _chat(messages, llamaserver_url=llamaserver_url, api_key=api_key)

    # Sources mirror the chunk result shape (minus the raw text, which is large) so the
    # UI can render the citation list / open the original PDF at the right page.
    sources = [
        {
            "id": item["id"],
            "source_path": item["source_path"],
            "title": item["title"],
            "awmf": item["awmf"],
            "society": item["society"],
            "page": item["page"],
            "score": item["score"],
        }
        for item in items
    ]

    return {
        "answer": answer.strip(),
        "sources": sources,
        "query": query,
        "model": model_used,
    }
