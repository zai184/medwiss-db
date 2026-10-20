"""Tests for CHUNK_SEARCH_MODE dispatch (embed vs keyword).

Pure-Python: the mode switch must route to the tsvector path without touching
the embed sidecar, and default stays embed. No DB, no network.
"""

from api.config import settings


class TestModeDispatch:
    def test_keyword_mode_routes_to_tsvector_path(self, monkeypatch):
        from search import chunks

        calls = {}

        def fake_keyword(query, db, limit=20, offset=0):
            calls["args"] = (query, db, limit, offset)
            return {"items": [], "total": 0, "query": query, "limit": limit, "offset": offset}

        def fail_embed(*a, **kw):
            raise AssertionError("embed path must not run in keyword mode")

        monkeypatch.setattr(settings, "chunk_search_mode", "keyword")
        monkeypatch.setattr(chunks, "_keyword_search_chunks", fake_keyword)
        monkeypatch.setattr(chunks, "embed_query", fail_embed)

        result = chunks.search_chunks("kopfschmerz", None, 5, 0)
        assert result["total"] == 0
        assert calls["args"] == ("kopfschmerz", None, 5, 0)

    def test_default_mode_uses_embed_path(self, monkeypatch):
        from search import chunks

        def fail_keyword(*a, **kw):
            raise AssertionError("keyword path must not run in embed mode")

        class FakeResult:
            def fetchall(self):
                return []

        class FakeDB:
            def execute(self, *a, **kw):
                return FakeResult()

        monkeypatch.setattr(settings, "chunk_search_mode", "embed")
        monkeypatch.setattr(chunks, "_keyword_search_chunks", fail_keyword)
        monkeypatch.setattr(chunks, "embed_query", lambda q, *a, **kw: [0.0] * 2048)
        monkeypatch.setattr(chunks, "_embedding_str", lambda v: "[0]")

        result = chunks.search_chunks("kopfschmerz", FakeDB(), 5, 0)
        assert result["total"] == 0

class TestKeywordSearchSQL:
    """Structural guard: the scalar tsquery alias must be used as ``q``, never ``q.tsq``.

    websearch_to_tsquery(...) returns a scalar tsquery, so aliasing it ``q`` names a
    single output column — ``q.tsq`` is an invalid reference that broke /search/chunks
    and /search/chunks/rag on the VPS (500). Execute the real function against a fake
    DB that captures the SQL text.
    """

    def test_where_and_score_reference_scalar_alias_q(self):
        from search import chunks

        captured = []

        class FakeResult:
            def fetchall(self):
                return []

            def scalar_one(self):
                return 0

        class FakeDB:
            def execute(self, stmt, params):
                captured.append(str(stmt))
                return FakeResult()

        chunks._keyword_search_chunks("kopfschmerz", FakeDB())

        # First execute is the main SELECT; the second is its count query.
        main_sql, count_sql = captured
        assert "c.search_vector @@ q" in main_sql
        assert "ts_rank(c.search_vector, q) AS score" in main_sql
        assert "q.tsq" not in main_sql
        # count query reuses the same WHERE with the scalar alias
        assert "c.search_vector @@ q" in count_sql
        assert "q.tsq" not in count_sql
