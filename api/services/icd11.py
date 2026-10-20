"""WHO ICD-11 API client with OAuth2 authentication."""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
SEARCH_URL = "https://id.who.int/icd/release/11/2026-01/mms/search"
# Search requires the versioned release path (2026-01); the unversioned /mms/search 404s


@dataclass
class ICD11Result:
    """Single ICD-11 search result."""

    code: str
    title: str
    uri: str


class ICD11Client:
    """OAuth2 client for the WHO ICD-11 API.

    Usage::

        client = ICD11Client(client_id="...", client_secret="...")
        results = await client.search("Vorhofflimmern")
        # [ICD11Result(code='BC81.3', title='Vorhofflimmern', uri='...')]
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        timeout: float = 15.0,
        max_concurrent: int = 5,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._token: str | None = None
        self._token_expires: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _ensure_token(self) -> str:
        """Get or refresh the OAuth2 access token."""
        if self._token and time.time() < self._token_expires:
            return self._token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "icdapi_access",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data: dict[str, str] = resp.json()

        token: str = token_data["access_token"]
        self._token = token
        # Cache for 55 minutes (token expires in 3600s)
        self._token_expires = time.time() + 3300
        return token

    async def search(
        self,
        query: str,
        *,
        language: str = "de",
        max_results: int = 5,
    ) -> list[ICD11Result]:
        """Search ICD-11 MMS for a diagnosis term.

        Returns up to ``max_results`` results, sorted by relevance.
        Returns empty list on any error (network, auth, rate limit).
        """
        if not self.is_configured:
            return []

        try:
            async with self._semaphore:
                token = await self._ensure_token()
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(
                        SEARCH_URL,
                        params={"q": query, "useFlexisearch": "true"},
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                            "Accept-Language": language,
                            "API-Version": "v2",
                        },
                    )
                    # Handle token expiry — refresh once and retry
                    if resp.status_code == 401:
                        self._token = None
                        self._token_expires = 0.0
                        token = await self._ensure_token()
                        resp = await client.get(
                            SEARCH_URL,
                            params={"q": query, "useFlexisearch": "true"},
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/json",
                                "Accept-Language": language,
                                "API-Version": "v2",
                            },
                        )
                    resp.raise_for_status()
        except Exception as e:
            logger.warning(f"ICD-11 search failed for '{query}': {e}")
            return []

        data: dict[str, object] = resp.json()
        entities_raw = data.get("destinationEntities", [])
        entities: list[dict[str, str]] = (
            entities_raw if isinstance(entities_raw, list) else []
        )
        import re

        results: list[ICD11Result] = []
        for entity in entities[:max_results]:
            code = str(entity.get("theCode", ""))
            title = str(entity.get("title", ""))
            uri = str(entity.get("id", ""))
            # Strip HTML markup from title (e.g. "<em class='found'>Kopfschmerz</em>")
            title = re.sub(r"<[^>]+>", "", title)
            if code and title:
                results.append(ICD11Result(code=code, title=title, uri=uri))
        return results
