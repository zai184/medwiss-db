"""Tests for the simple keyword search (search.keyword).

Pure-Python tests on the ILIKE pattern building and the SQL shape. No DB needed.
"""



class TestLikePattern:
    """The ILIKE pattern must be a substring pattern with escaped metacharacters."""

    def test_simple_term(self):
        from search.keyword import like_pattern

        assert like_pattern("pneumonie") == "%pneumonie%"

    def test_strips_whitespace(self):
        from search.keyword import like_pattern

        assert like_pattern("  herz  ") == "%herz%"

    def test_empty_returns_wildcard_only(self):
        from search.keyword import like_pattern

        assert like_pattern("") == "%%"
        assert like_pattern("   ") == "%%"

    def test_escapes_percent(self):
        from search.keyword import like_pattern

        assert like_pattern("100%") == "%100\\%%"

    def test_escapes_underscore(self):
        from search.keyword import like_pattern

        assert like_pattern("c_d") == "%c\\_d%"

    def test_escapes_backslash(self):
        from search.keyword import like_pattern

        assert like_pattern("a\\b") == "%a\\\\b%"

    def test_pattern_produces_valid_regex_equivalent(self):
        """Escaped pattern should match literally when translated back to regex."""
        from search.keyword import like_pattern

        pat = like_pattern("a_b%c")
        # Unescape for regex literal use
        literal = pat[1:-1].replace("\\", "")
        assert literal == "a_b%c"


class TestSearchSQL:
    """Structural checks on the generated SQL."""

    def test_sql_uses_ilike_and_named_params(self):
        from search.keyword import _SEARCH_SQL

        assert "ILIKE" in _SEARCH_SQL
        assert "ESCAPE" in _SEARCH_SQL
        assert "knowledge_entries" in _SEARCH_SQL
        assert ":limit" in _SEARCH_SQL
        assert ":offset" in _SEARCH_SQL

    def test_sql_covers_all_search_fields(self):
        from search.keyword import _SEARCH_SQL

        assert "ke.titel" in _SEARCH_SQL
        assert "ke.inhalt" in _SEARCH_SQL
        assert "ke.zusammenfassung" in _SEARCH_SQL
        assert "ke.source_path" in _SEARCH_SQL
        assert "source_hierarchy" in _SEARCH_SQL
        # Keyword search must not scan chunks (594k AWMF rows; ILIKE EXISTS melts CPU).
        assert "chunks" not in _SEARCH_SQL

    def test_where_builder_does_not_take_a_chunk_clause(self):
        import inspect

        from search.keyword import _build_where

        assert "chunk" not in inspect.signature(_build_where).parameters

    def test_no_fts_or_vector_constructs(self):
        from search.keyword import _SEARCH_SQL

        for banned in ("tsquery", "ts_rank", "<=>", "similarity", "v_entry_search"):
            assert banned not in _SEARCH_SQL


class TestBuildWhere:
    """The WHERE builder ANDs the keyword OR-group with filter clauses."""

    def test_no_query_no_filters_is_true(self):
        from search.keyword import _build_where

        assert _build_where("", None) == "TRUE"

    def test_query_only_wraps_keyword_or_group(self):
        from search.keyword import _build_where

        where = _build_where("herz", None)
        assert where.startswith("(") and where.endswith(")")
        assert "ke.titel ILIKE" in where
        assert "chunks" not in where

    def test_filters_are_anded(self):
        from search.keyword import _build_where

        where = _build_where(
            "herz", {"fach_id": 3, "dokumenttyp": (7, "Leitlinie"), "folder": "1_SOPs"},
        )
        parts = where.split(" AND ")
        assert len(parts) == 5  # keyword group + 3 filters (fach EXISTS has 1 inner AND)
        assert "entry_fach" in where and "fachgebiete" in where
        assert ":fach_id" in where
        assert "ke.dokumenttyp_id = :dokumenttyp_id" in where
        assert "ke.dokumenttyp = :dokumenttyp_name" in where
        assert "ke.source_hierarchy ->> 0 = :folder" in where

    def test_filters_without_query(self):
        from search.keyword import _build_where

        where = _build_where("", {"folder": "1_SOPs"})
        assert where == "ke.source_hierarchy ->> 0 = :folder"


class TestSearchKeywordFilters:
    """Filter resolution and combination behavior (fake DB)."""

    def _fake_db(self, resolves=None, chunk_table=True):
        class _Result:
            def __init__(self, value):
                self._value = value

            def scalar(self):
                return self._value

            def first(self):
                return self._value

            def fetchall(self):
                return []

        class _FakeDB:
            def __init__(self):
                self.queries = []

            def execute(self, sql, params=None):
                self.queries.append((str(sql), params or {}))
                key = str(sql)
                if resolves and key in resolves:
                    return _Result(resolves[key])
                if "to_regclass" in key:
                    return _Result("public.chunks" if chunk_table else None)
                return _Result(None)

        return _FakeDB()

    def test_unknown_fachgebiet_raises(self):
        import pytest

        from search.keyword import search_keyword

        db = self._fake_db()  # resolution query returns None
        with pytest.raises(ValueError):
            search_keyword(db, "herz", fachgebiet="999")

    def test_filter_combination_builds_anded_sql(self):
        from search.keyword import search_keyword

        fach_row = type("R", (), {"id": 3})()
        dt_row = type("R", (), {"id": 7, "name": "Leitlinie"})()
        db = self._fake_db(resolves={
            "SELECT id FROM fachgebiete WHERE id = :v OR lower(name) = lower(:name) LIMIT 1": fach_row,
            "SELECT id, name FROM dokumenttypen WHERE id = :v OR lower(name) = lower(:name) LIMIT 1": dt_row,
        })
        search_keyword(db, "herz", fachgebiet="3", dokumenttyp="Leitlinie", folder="1_SOPs")
        count_sql, count_params = next(q for q in db.queries if "COUNT(*)" in q[0])
        assert count_sql.count(" AND ") >= 3
        assert "ke.titel % :raw" in count_sql
        assert count_params == {
            "pat": "%herz%", "raw": "herz", "fach_id": 3, "dokumenttyp_id": 7,
            "dokumenttyp_name": "Leitlinie", "folder": "1_SOPs",
        }

    def test_empty_query_with_filters_still_runs(self):
        from search.keyword import search_keyword

        db = self._fake_db()
        items, total = search_keyword(db, "", folder="1_SOPs")
        assert items == [] and total == 0
        # count + search executed (no short-circuit)
        assert len(db.queries) >= 2

    def test_filter_only_sql_does_not_mention_chunks(self):
        from search.keyword import search_keyword

        db = self._fake_db()
        search_keyword(db, "", folder="1_SOPs")
        assert all("chunks" not in sql for sql, _ in db.queries)

    def test_empty_query_no_filters_short_circuits(self):
        from search.keyword import search_keyword

        db = self._fake_db()
        items, total = search_keyword(db, "")
        assert items == [] and total == 0
        assert db.queries == []


class TestFilterOptions:
    """filter_options returns the five tag dimensions plus folders, with counts."""

    def test_options_shape(self):
        from search.keyword import filter_options

        rows = {
            "fachgebiete": [type("R", (), {"id": 1, "name": "Kardiologie", "cnt": 9})()],
            "diagnosen": [type("R", (), {"id": 2, "name": "Diabetes", "cnt": 7})()],
            "symptome": [type("R", (), {"id": 3, "name": "Brustschmerz", "cnt": 5})()],
            "dokumenttypen": [type("R", (), {"id": 4, "name": "Leitlinie", "cnt": 11})()],
            "ordner_labels": [type("R", (), {"id": 5, "name": "Wichtig", "cnt": 3})()],
            "folders": [type("R", (), {"name": "1_SOPs", "entry_count": 12})()],
        }

        class _Result:
            def __init__(self, r):
                self._rows = r

            def fetchall(self):
                return self._rows

        class _FakeDB:
            def execute(self, sql, params=None):
                key = str(sql)
                for table in (
                    "fachgebiete",
                    "diagnosen",
                    "symptome",
                    "dokumenttypen",
                    "ordner_labels",
                ):
                    if table in key:
                        return _Result(rows[table])
                # FOLDER_SQL selects from knowledge_entries on source_hierarchy.
                assert "source_hierarchy" in key
                return _Result(rows["folders"])

        opts = filter_options(_FakeDB())
        assert opts == {
            "fachgebiete": [{"id": 1, "name": "Kardiologie", "count": 9}],
            "diagnosen": [{"id": 2, "name": "Diabetes", "count": 7}],
            "symptome": [{"id": 3, "name": "Brustschmerz", "count": 5}],
            "dokumenttypen": [{"id": 4, "name": "Leitlinie", "count": 11}],
            "ordner_labels": [{"id": 5, "name": "Wichtig", "count": 3}],
            "folders": [{"name": "1_SOPs", "count": 12}],
        }


class TestSearchRouterForwardsFilters:
    def test_endpoint_passes_fachgebiet_and_dokumenttyp(self):
        import inspect

        from api.routers import search as search_router

        src = inspect.getsource(search_router.search)
        assert "fachgebiet=fachgebiet" in src
        assert "dokumenttyp=dokumenttyp" in src


class TestShortCircuit:
    def test_search_short_circuits_blank_query_no_filters(self):
        from search.keyword import search_keyword

        class _FakeDB:
            def execute(self, *a, **k):  # pragma: no cover - must not be called
                raise AssertionError("DB must not be hit for an empty query")

        items, total = search_keyword(_FakeDB(), "   ")
        assert items == []
        assert total == 0
