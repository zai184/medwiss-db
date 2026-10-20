"""Simple keyword search over knowledge entries.

ILIKE substring matching with tier ranking (title > filename > folder
segment > content), optionally filtered by fachgebiet, dokumenttyp, folder,
diagnose, symptom and ordner-label. Filters AND across categories.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Tier score: title (3) > fuzzy title, trigram `%` — typo tolerance (2) = filename (2)
# > folder segment (1.5) > content (1).
# Do not JOIN/EXISTS the chunks table here: ~594k AWMF rows × ILIKE per entry
# pegs CPU and never returns. PDF/chunk search lives on /search/chunks.
_SEARCH_SQL = """
SELECT
    ke.id,
    ke.titel,
    ke.zusammenfassung,
    ke.inhalt,
    ke.dokumenttyp,
    ke.unterkategorie,
    ke.source_path,
    ke.schwierigkeit,
    ke.created_at,
    ke.updated_at,
    (CASE WHEN ke.titel ILIKE :pat ESCAPE '\\' THEN 3 ELSE 0 END)
  + (CASE WHEN regexp_replace(COALESCE(ke.source_path, ''), '^.*/', '')
          ILIKE :pat ESCAPE '\\' THEN 2 ELSE 0 END)
  + (CASE WHEN COALESCE((SELECT string_agg(seg, ' ')
            FROM jsonb_array_elements_text(ke.source_hierarchy) seg), '')
          ILIKE :pat ESCAPE '\\' THEN 1.5 ELSE 0 END)
  + (CASE WHEN ke.inhalt ILIKE :pat ESCAPE '\\'
               OR ke.zusammenfassung ILIKE :pat ESCAPE '\\' THEN 1 ELSE 0 END)
  + (CASE WHEN ke.titel % :raw THEN 2 ELSE 0 END) AS rank
FROM knowledge_entries ke
WHERE {where}
ORDER BY rank DESC, ke.updated_at DESC
LIMIT :limit OFFSET :offset
"""

_FACH_EXISTS = """
     EXISTS (
        SELECT 1 FROM entry_fach ef
        JOIN fachgebiete fg ON fg.id = ef.fach_id
        WHERE ef.entry_id = ke.id
          AND fg.id = :fach_id
   )"""

_LABEL_EXISTS = """
     EXISTS (
        SELECT 1 FROM {junction} j
        WHERE j.entry_id = ke.id
          AND j.{column} = :{param}
   )"""

_DOKUMENTTYP_MATCH = """
     (ke.dokumenttyp_id = :dokumenttyp_id
      OR ke.dokumenttyp = :dokumenttyp_name)"""

_FOLDER_MATCH = "ke.source_hierarchy ->> 0 = :folder"

_FILTER_OPTIONS_FACH_SQL = """
SELECT fg.id, fg.name, COUNT(ef.entry_id) AS cnt
FROM fachgebiete fg
JOIN entry_fach ef ON ef.fach_id = fg.id
GROUP BY fg.id, fg.name
ORDER BY cnt DESC, fg.name
"""
_FILTER_OPTIONS_DT_SQL = """
SELECT d.id, d.name, COUNT(ke.id) AS cnt
FROM dokumenttypen d
JOIN knowledge_entries ke ON ke.dokumenttyp_id = d.id
GROUP BY d.id, d.name
ORDER BY cnt DESC, d.name
"""
_FILTER_OPTIONS_FOLDER_SQL = """
SELECT ke.source_hierarchy ->> 0 AS name, COUNT(*) AS entry_count
FROM knowledge_entries ke
WHERE ke.source_hierarchy ->> 0 IS NOT NULL
GROUP BY ke.source_hierarchy ->> 0
ORDER BY name
"""
_FILTER_OPTIONS_DIAG_SQL = """
SELECT d.id, d.name, COUNT(j.entry_id) AS cnt
FROM diagnosen d
JOIN entry_diagnose j ON j.diagnose_id = d.id
GROUP BY d.id, d.name
ORDER BY cnt DESC, d.name
"""
_FILTER_OPTIONS_SYM_SQL = """
SELECT s.id, s.name, COUNT(j.entry_id) AS cnt
FROM symptome s
JOIN entry_symptom j ON j.symptom_id = s.id
GROUP BY s.id, s.name
ORDER BY cnt DESC, s.name
"""
_FILTER_OPTIONS_OL_SQL = """
SELECT ol.id, ol.name, COUNT(j.entry_id) AS cnt
FROM ordner_labels ol
JOIN entry_ordner_label j ON j.label_id = ol.id
GROUP BY ol.id, ol.name
ORDER BY cnt DESC, ol.name
LIMIT 50
"""


def like_pattern(query: str) -> str:
    """Turn a raw query into a safe ILIKE pattern (escapes %, _ and \\)."""
    escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _build_where(query: str | None, filters: dict | None) -> str:
    """Assemble the WHERE clause: keyword OR-group ANDed with filter clauses."""
    parts: list[str] = []
    if query and query.strip():
        parts.append(
            "(ke.titel ILIKE :pat ESCAPE '\\'"
            " OR regexp_replace(COALESCE(ke.source_path, ''), '^.*/', '')"
            " ILIKE :pat ESCAPE '\\'"
            " OR COALESCE((SELECT string_agg(seg, ' ')"
            "        FROM jsonb_array_elements_text(ke.source_hierarchy) seg), '')"
            " ILIKE :pat ESCAPE '\\'"
            " OR ke.inhalt ILIKE :pat ESCAPE '\\'"
            " OR ke.zusammenfassung ILIKE :pat ESCAPE '\\'"
            " OR ke.titel % :raw)"
        )
    if filters:
        for key in ("fach_id", "diagnose_id", "symptom_id", "ordner_label_id"):
            if filters.get(key) is not None:
                parts.append(_EXISTS_BY_KEY[key])
        dt = filters.get("dokumenttyp")
        if dt is not None:
            parts.append(_DOKUMENTTYP_MATCH)
        folder = filters.get("folder")
        if folder:
            parts.append(_FOLDER_MATCH)
    return " AND ".join(parts) if parts else "TRUE"


_FACH_SQL = "SELECT id FROM fachgebiete WHERE id = :v OR lower(name) = lower(:name) LIMIT 1"
_LABEL_SQL = "SELECT id FROM {table} WHERE id = :v OR lower(name) = lower(:name) LIMIT 1"
_DT_SQL = "SELECT id, name FROM dokumenttypen WHERE id = :v OR lower(name) = lower(:name) LIMIT 1"
_EXISTS_BY_KEY = {
    "fach_id": _FACH_EXISTS,
    "diagnose_id": _LABEL_EXISTS.format(junction="entry_diagnose", column="diagnose_id", param="diagnose_id"),
    "symptom_id": _LABEL_EXISTS.format(junction="entry_symptom", column="symptom_id", param="symptom_id"),
    "ordner_label_id": _LABEL_EXISTS.format(junction="entry_ordner_label", column="label_id", param="ordner_label_id"),
}
_RESOLVE_SQL = {
    "diagnose": "diagnosen",
    "symptom": "symptome",
    "ordner_label": "ordner_labels",
}


def resolve_fachgebiet(db: Session, value: str) -> int | None:
    """Resolve a fachgebiet by id or (case-insensitive) name. None if unknown."""
    v = value.strip()
    row = db.execute(
        text(_FACH_SQL), {"v": int(v) if v.isdigit() else -1, "name": v}
    ).first()
    return row.id if row else None


def resolve_label(db: Session, dimension: str, value: str) -> int | None:
    """Resolve a diagnose/symptom/ordner_label by id or (case-insensitive) name."""
    v = value.strip()
    row = db.execute(
        text(_LABEL_SQL.format(table=_RESOLVE_SQL[dimension])),
        {"v": int(v) if v.isdigit() else -1, "name": v},
    ).first()
    return row.id if row else None


def resolve_dokumenttyp(db: Session, value: str) -> tuple[int, str] | None:
    """Resolve a dokumenttyp by id or name. Returns (id, name) for the SQL match."""
    v = value.strip()
    row = db.execute(
        text(_DT_SQL), {"v": int(v) if v.isdigit() else -1, "name": v}
    ).first()
    if not row:
        # Legacy string-only match: entry has a dokumenttyp string with no
        # dokumenttypen row (dual-write convention).
        return (-1, v) if not v.isdigit() else None
    return (row.id, row.name)


def search_keyword(
    db: Session,
    query: str = "",
    limit: int = 20,
    offset: int = 0,
    fachgebiet: str | None = None,
    dokumenttyp: str | None = None,
    folder: str | None = None,
    diagnose: str | None = None,
    symptom: str | None = None,
    ordner_label: str | None = None,
) -> tuple[list[dict], int]:
    """Run the keyword search. Returns (rows as dicts, total matches).

    Filters (fachgebiet/dokumenttyp/folder/diagnose/symptom/ordner_label) are
    plain WHERE clauses ANDed on top of the keyword match. Empty query with
    filters lists all entries matching the filters.
    """
    filters: dict = {}
    if fachgebiet:
        fach_id = resolve_fachgebiet(db, fachgebiet)
        if fach_id is None:
            raise ValueError(f"Unknown fachgebiet: {fachgebiet!r}")
        filters["fach_id"] = fach_id
    if dokumenttyp:
        dt = resolve_dokumenttyp(db, dokumenttyp)
        if dt is None:
            raise ValueError(f"Unknown dokumenttyp: {dokumenttyp!r}")
        filters["dokumenttyp"] = dt
    if folder:
        filters["folder"] = folder
    for dimension, key in (
        ("diagnose", "diagnose_id"),
        ("symptom", "symptom_id"),
        ("ordner_label", "ordner_label_id"),
    ):
        value = {"diagnose": diagnose, "symptom": symptom, "ordner_label": ordner_label}[dimension]
        if value:
            label_id = resolve_label(db, dimension, value)
            if label_id is None:
                raise ValueError(f"Unknown {dimension}: {value!r}")
            filters[key] = label_id
    if not query.strip() and not filters:
        return [], 0

    sql_params: dict = {"pat": like_pattern(query), "raw": query.strip()}
    if "fach_id" in filters:
        sql_params["fach_id"] = filters["fach_id"]
    if "dokumenttyp" in filters:
        sql_params["dokumenttyp_id"] = filters["dokumenttyp"][0]
        sql_params["dokumenttyp_name"] = filters["dokumenttyp"][1]
    if "folder" in filters:
        sql_params["folder"] = filters["folder"]
    for key in ("diagnose_id", "symptom_id", "ordner_label_id"):
        if key in filters:
            sql_params[key] = filters[key]

    where = _build_where(query, filters)
    count_sql = text(
        f"SELECT COUNT(*) FROM knowledge_entries ke WHERE {where}"
    )
    search_sql = text(_SEARCH_SQL.replace("{where}", where))
    params = {**sql_params, "limit": limit, "offset": offset}
    total = db.execute(count_sql, sql_params).scalar() or 0
    rows = db.execute(search_sql, params).fetchall()

    items = [
        {
            "id": row.id,
            "titel": row.titel,
            "zusammenfassung": row.zusammenfassung,
            "inhalt": row.inhalt,
            "dokumenttyp": row.dokumenttyp,
            "unterkategorie": row.unterkategorie,
            "source_path": row.source_path,
            "schwierigkeit": row.schwierigkeit,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "rank": float(row.rank),
        }
        for row in rows
    ]
    return items, total


def _counted_options(db: Session, sql: str) -> list[dict]:
    return [
        {"id": r.id, "name": r.name, "count": int(r.cnt)}
        for r in db.execute(text(sql)).fetchall()
    ]


def filter_options(db: Session) -> dict:
    """Filter options for the UI: the five tag dimensions with entry counts
    (grouped junction queries, count desc; ordner labels capped at 50) plus
    top-level folders."""
    return {
        "fachgebiete": _counted_options(db, _FILTER_OPTIONS_FACH_SQL),
        "diagnosen": _counted_options(db, _FILTER_OPTIONS_DIAG_SQL),
        "symptome": _counted_options(db, _FILTER_OPTIONS_SYM_SQL),
        "dokumenttypen": _counted_options(db, _FILTER_OPTIONS_DT_SQL),
        "ordner_labels": _counted_options(db, _FILTER_OPTIONS_OL_SQL),
        "folders": [
            {"name": r.name, "count": int(r.entry_count)}
            for r in db.execute(text(_FILTER_OPTIONS_FOLDER_SQL)).fetchall()
        ],
    }