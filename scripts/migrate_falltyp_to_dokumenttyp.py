#!/usr/bin/env python3
"""Migrate falltyp → dokumenttyp and drop falltyp column.

Usage:
    python scripts/migrate_falltyp_to_dokumenttyp.py
    python scripts/migrate_falltyp_to_dokumenttyp.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings
from api.services.hierarchy_labels import CATEGORY_LABELS

# Legacy manual edit-form values
LEGACY_FALLTYP = {
    "lehrfall": "Fall",
    "richtlinien": "Leitlinie",
    "forschung": "Studie",
}

MAPPING = {**{k: v for k, v in CATEGORY_LABELS.items()}, **LEGACY_FALLTYP}


def column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def build_case_sql() -> str:
    parts = ["CASE LOWER(TRIM(falltyp))"]
    for key, label in MAPPING.items():
        parts.append(f"  WHEN '{key}' THEN '{label.replace(chr(39), chr(39)+chr(39))}'")
    parts.append("  ELSE INITCAP(REPLACE(REPLACE(falltyp, '_', ' '), '-', ' '))")
    parts.append("END")
    return "\n".join(parts)


VIEW_SQL = """
DROP VIEW IF EXISTS v_entry_search CASCADE;

CREATE VIEW v_entry_search AS
SELECT
    ke.id AS entry_id,
    ke.titel,
    ke.zusammenfassung,
    ke.inhalt,
    ke.dokumenttyp,
    ke.schwierigkeit,
    ke.unterkategorie,
    ke.status,
    ke.search_vector,
    ke.created_at,
    ke.updated_at,
    COALESCE(
        (
            SELECT ARRAY(
                SELECT DISTINCT unnest(
                    COALESCE(
                        ARRAY_AGG(DISTINCT f.name) FILTER (WHERE f.name IS NOT NULL),
                        ARRAY[]::VARCHAR[]
                    ) || COALESCE(
                        ARRAY(SELECT jsonb_array_elements_text(ke.source_hierarchy)),
                        ARRAY[]::VARCHAR[]
                    )
                )
            )
        ),
        ARRAY[]::VARCHAR[]
    ) AS fachgebiete_names,
    COALESCE(
        ARRAY_AGG(DISTINCT f.id) FILTER (WHERE f.id IS NOT NULL),
        ARRAY[]::INTEGER[]
    ) AS fachgebiete_ids,
    COALESCE(string_agg(DISTINCT f.name, ' ') FILTER (WHERE f.name IS NOT NULL), '') || ' ' ||
    COALESCE((SELECT string_agg(elem, ' ') FROM jsonb_array_elements_text(ke.source_hierarchy) AS elem), '')
        AS fachgebiete_text,
    COALESCE(
        ARRAY_AGG(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL),
        ARRAY[]::VARCHAR[]
    ) AS diagnosen_names,
    COALESCE(
        ARRAY_AGG(DISTINCT d.id) FILTER (WHERE d.id IS NOT NULL),
        ARRAY[]::INTEGER[]
    ) AS diagnosen_ids,
    string_agg(DISTINCT d.name, ' ') FILTER (WHERE d.name IS NOT NULL) AS diagnosen_text,
    COALESCE(
        ARRAY_AGG(DISTINCT s.name) FILTER (WHERE s.name IS NOT NULL),
        ARRAY[]::VARCHAR[]
    ) AS symptome_names,
    COALESCE(
        ARRAY_AGG(DISTINCT s.id) FILTER (WHERE s.id IS NOT NULL),
        ARRAY[]::INTEGER[]
    ) AS symptome_ids,
    string_agg(DISTINCT s.name, ' ') FILTER (WHERE s.name IS NOT NULL) AS symptome_text,
    (
        ke.search_vector ||
        setweight(to_tsvector('german', COALESCE(string_agg(DISTINCT f.name, ' '), '')), 'C') ||
        setweight(to_tsvector('german', COALESCE(
            (SELECT string_agg(elem, ' ') FROM jsonb_array_elements_text(ke.source_hierarchy) AS elem), ''
        )), 'C') ||
        setweight(to_tsvector('german', COALESCE(string_agg(DISTINCT d.name, ' '), '')), 'C') ||
        setweight(to_tsvector('german', COALESCE(string_agg(DISTINCT s.name, ' '), '')), 'C')
    ) AS full_search_vector
FROM
    knowledge_entries ke
    LEFT JOIN entry_fach ef ON ke.id = ef.entry_id
    LEFT JOIN fachgebiete f ON ef.fach_id = f.id
    LEFT JOIN entry_diagnose ed ON ke.id = ed.entry_id
    LEFT JOIN diagnosen d ON ed.diagnose_id = d.id
    LEFT JOIN entry_symptom es ON ke.id = es.entry_id
    LEFT JOIN symptome s ON es.symptom_id = s.id
GROUP BY
    ke.id, ke.titel, ke.zusammenfassung, ke.inhalt, ke.dokumenttyp,
    ke.schwierigkeit, ke.unterkategorie, ke.status, ke.search_vector,
    ke.source_hierarchy, ke.created_at, ke.updated_at
"""


def run_migration(db: Session, dry_run: bool = False) -> None:
    if not column_exists(db, "knowledge_entries", "falltyp"):
        print("Column falltyp already dropped. Recreating view only.")
        if not dry_run:
            db.execute(text(VIEW_SQL))
            db.commit()
        return

    case_sql = build_case_sql()
    migrate_sql = f"""
        UPDATE knowledge_entries
        SET dokumenttyp = {case_sql}
        WHERE falltyp IS NOT NULL AND TRIM(falltyp) != ''
    """

    if dry_run:
        print("[DRY RUN] Would run:")
        print(migrate_sql)
        print("ALTER TABLE knowledge_entries DROP COLUMN falltyp;")
        print("DROP INDEX IF EXISTS idx_knowledge_entries_falltyp;")
        print("CREATE INDEX idx_knowledge_entries_dokumenttyp ...")
        return

    print("Migrating falltyp → dokumenttyp...")
    result = db.execute(text(migrate_sql))
    print(f"  Updated {result.rowcount} rows")

    stats = db.execute(
        text(
            "SELECT dokumenttyp, COUNT(*) FROM knowledge_entries "
            "GROUP BY dokumenttyp ORDER BY COUNT(*) DESC"
        )
    ).fetchall()
    print("Dokumenttyp distribution:")
    for row in stats:
        print(f"  {row[0]}: {row[1]}")

    print("Dropping dependent views...")
    db.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_entry_search CASCADE"))
    db.execute(text("DROP VIEW IF EXISTS v_entry_search CASCADE"))

    print("Dropping falltyp column...")
    db.execute(text("DROP INDEX IF EXISTS idx_knowledge_entries_falltyp"))
    db.execute(text("ALTER TABLE knowledge_entries DROP COLUMN falltyp"))
    if not column_exists(db, "knowledge_entries", "dokumenttyp"):
        raise RuntimeError("dokumenttyp column missing")
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_entries_dokumenttyp "
            "ON knowledge_entries(dokumenttyp)"
        )
    )
    print("Recreating v_entry_search...")
    db.execute(text(VIEW_SQL))
    db.commit()
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        run_migration(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
