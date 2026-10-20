"""OpenRouter vision OCR client (image/PDF → text) for the on-demand seam.

Sends each page/image to a vision model (default `z-ai/glm-4.6v`) via
OpenRouter chat-completions using the existing OPENROUTER_API_KEY — no extra
provider or key. PDFs are rasterized page-by-page with pymupdf (pure wheel,
no poppler) via a generator so a many-page PDF never materializes a full page
list in memory (important on the 2 GB VPS).

Reachable only from pipeline.ocr_backend (on-demand). No batch use.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Callable, Iterator

import httpx

from api.config import settings
from pipeline.ocr_backend import _BackendUnavailable

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_DEFAULT_DPI = 180


def _with_retries(
    call: Callable[[httpx.Timeout], httpx.Response], path: Path
) -> httpx.Response:
    """POST with exponential backoff on 429/5xx/connect; deterministic on 4xx.

    Returns the final response (2xx). Raises _BackendUnavailable on 401/403/
    413 immediately, or after retries are exhausted for transient errors.
    """
    timeout = httpx.Timeout(
        connect=10,
        read=settings.ocr_remote_timeout_seconds,
        write=120,
        pool=10,
    )
    attempt = 0
    while True:
        try:
            response = call(timeout)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
            attempt += 1
            if attempt >= _MAX_RETRIES:
                raise _BackendUnavailable(
                    f"{path.name}: remote unreachable after {attempt} tries: {e}"
                ) from e
            time.sleep(1.0 * attempt)
            continue

        if response.status_code in (401, 403):
            raise _BackendUnavailable(f"{path.name}: auth rejected ({response.status_code})")
        if response.status_code == 413:
            raise _BackendUnavailable(f"{path.name}: payload too large ({response.status_code})")

        if response.status_code == 429:
            raise _BackendUnavailable(
                f"{path.name}: rate limited (429) after {attempt + 1} tries"
            )

        if response.status_code >= 500:
            attempt += 1
            if attempt >= _MAX_RETRIES:
                raise _BackendUnavailable(
                    f"{path.name}: remote failed after {attempt} tries "
                    f"(status {response.status_code})"
                )
            time.sleep(1.0 * attempt)
            continue

        response.raise_for_status()  # other 4xx -> HTTPStatusError (runtime failure)
        return response


def _pdf_page_generator(path: Path, dpi: int = _DEFAULT_DPI) -> Iterator[bytes]:
    """Yield each PDF page rendered to PNG bytes, one at a time (memory guard).

    Streams pages instead of building a list so a many-page PDF on a small box
    does not OOM.
    """
    import fitz  # pymupdf (pure wheel, no poppler)

    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            yield pix.tobytes("png")
            del pix


def openrouter_vision_extract(path: Path) -> str:
    """Extract text via a vision model (default glm-4.6v), page by page.

    Raises _BackendUnavailable if OPENROUTER_API_KEY is unset or the remote
    rejects deterministically; runtime failures on other 4xx.
    """
    if not settings.openrouter_api_key:
        raise _BackendUnavailable("OPENROUTER_API_KEY not set")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    is_pdf = path.suffix.lower() == ".pdf"

    pages_text: list[str] = []
    pages = _pdf_page_generator(path) if is_pdf else iter([path.read_bytes()])

    for i, page_bytes in enumerate(pages):
        if i >= settings.ocr_max_pages:
            logger.warning(f"{path.name}: truncated after {settings.ocr_max_pages} pages")
            break

        def call(timeout: httpx.Timeout):
            return httpx.post(
                url,
                headers=headers,
                json={
                    "model": settings.openrouter_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": "data:image/png;base64,"
                                        + base64.b64encode(page_bytes).decode("ascii")
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Transcribe all text in this image verbatim.",
                                },
                            ],
                        }
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.0,
                },
                timeout=timeout,
            )

        response = _with_retries(call, path)
        content = response.json()["choices"][0]["message"]["content"]
        pages_text.append(f"--- Page {i + 1} ---\n{content}")

    return "\n\n".join(pages_text)
