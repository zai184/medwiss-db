"""Tests for AWMF chunk vector search.

Pure-Python unit tests on `search.chunks`: the instruct-prefix + MRL slice/normalize
embedding contract, dimension enforcement, and the service's error handling. No live DB.
"""

import pytest


class TestEmbedQuery:
    """Tests for the query-side embedding contract (instruct prefix + MRL slice→normalize)."""

    def _embed(self, monkeypatch, fake_response=None, fake_error=None):
        """Call embed_query with a stubbed httpx client."""
        from search import chunks

        class _FakeData:
            def __init__(self, embedding):
                self._embedding = embedding

            def __getitem__(self, _):
                return {"embedding": self._embedding}

        class _FakeResp:
            def raise_for_status(self):
                if fake_error:
                    raise fake_error
                return None

            def json(self):
                return {"data": [{"embedding": fake_response}]}

        import httpx

        class _FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, json=None, headers=None):
                assert "/v1/embeddings" in url
                # Assert the instruct prefix + model are sent
                assert json and json["input"][0].startswith(chunks.INSTRUCT_PREFIX)
                assert json["model"] == "qwen3emb8b"
                return _FakeResp()

        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeClient())
        return chunks

    def test_embed_query_slices_to_2048(self, monkeypatch):
        """A 4096-dim response is sliced to 2048."""
        _chunks = self._embed(monkeypatch, fake_response=[float(i) for i in range(4096)])
        vec = _chunks.embed_query("test query")
        assert len(vec) == 2048

    def test_embed_query_normalizes(self, monkeypatch):
        """Sliced vector is L2-normalized (norm ≈ 1)."""
        _chunks = self._embed(
            monkeypatch,
            fake_response=[1.0] * 4096,  # all-ones → slice of 2048 ones
        )
        vec = _chunks.embed_query("query")
        norm = sum(x * x for x in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-4

    def test_embed_query_empty_raises(self, monkeypatch):
        _chunks = self._embed(monkeypatch, fake_response=[1.0] * 2048)
        with pytest.raises(_chunks.EmbeddingError):
            _chunks.embed_query("   ")

    def test_embed_query_connect_error(self, monkeypatch):
        """Sidecar unreachable → LlamaserverConnectionError (maps to 503)."""
        import httpx

        class _ErrClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **kw):
                raise httpx.ConnectError("refused")

        _chunks = self._embed(monkeypatch, fake_error=httpx.ConnectError("x"))
        monkeypatch.setattr(httpx, "Client", lambda **kw: _ErrClient())
        with pytest.raises(_chunks.LlamaserverConnectionError):
            _chunks.embed_query("query")


class TestSearchChunks:
    """Empty-query short-circuit (no DB needed)."""

    def test_empty_query_returns_empty(self):
        from search.chunks import search_chunks

        class _FakeDB:
            pass

        res = search_chunks("   ", _FakeDB())
        assert res["items"] == []
        assert res["total"] == 0

    def test_search_chunks_prefixes_instruct(self, monkeypatch):
        """A real query embeds with the instruct prefix (via embed_query stub)."""
        from search.chunks import search_chunks

        captured = {}

        def fake_embed(q, url=None, api_key=None):
            captured["q"] = q
            return [0.5] * 2048

        # Normally search_chunks calls modules.embed_query; stub it at call time
        import search.chunks as mod

        monkeypatch.setattr(mod, "embed_query", fake_embed)

        class _FakeDB:
            def execute(self, *a, **kw):
                # count + select; return empty result list
                return _FakeResult()

        class _FakeResult:
            def scalar(self):
                return 0

            def fetchall(self):
                return []

        res = search_chunks("Bluthochdruck", _FakeDB())
        # The module's own search path asserts the prefix contract; here we confirm
        # search_chunks passes the raw query (prefix applied inside the real embed_query).
        assert captured["q"] == "Bluthochdruck"
        assert res["total"] == 0

    def test_instruct_prefix_shape(self):
        """The prefix matches the Leitlinien corpus convention exactly."""
        from search.chunks import INSTRUCT_PREFIX

        assert "retrieve relevant guideline passages" in INSTRUCT_PREFIX
        assert INSTRUCT_PREFIX.startswith("Instruct: Given a German medical guideline query")
        assert "\nQuery: " in INSTRUCT_PREFIX
