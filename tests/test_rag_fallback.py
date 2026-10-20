"""Tests for the RAG chat fallback chain (llamaserver → OpenRouter).

Pure-Python unit tests on `search.rag._chat`: provider order, fallback on
connect failures, and no-fallback without an OPENROUTER_API_KEY. No live DB,
no network.
"""

import httpx
import pytest

from api.config import settings

MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]


class _FakeResp:
    def __init__(self, url):
        self._url = url

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": f"answer via {self._url}"}}]}


class _FakeClient:
    """Simulates llamaserver (:8080) down; every other URL succeeds."""

    def __init__(self, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None, headers=None):
        if ":8080" in url:
            raise httpx.ConnectError(f"connection refused: {url}")
        return _FakeResp(url)


class TestChatFallback:
    def test_falls_back_to_openrouter_when_llamaserver_down(self, monkeypatch):
        from search import rag

        monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
        monkeypatch.setattr(httpx, "Client", _FakeClient)

        content, model = rag._chat(MESSAGES)
        assert "openrouter.ai" in content
        assert model == settings.openrouter_fallback_model
        assert model == "deepseek/deepseek-v4-flash"

    def test_raises_when_no_fallback_configured(self, monkeypatch):
        from search import rag

        monkeypatch.setattr(settings, "openrouter_api_key", "")
        monkeypatch.setattr(httpx, "Client", _FakeClient)

        with pytest.raises(rag.RagLlamaserverError):
            rag._chat(MESSAGES)


