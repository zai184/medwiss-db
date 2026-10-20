#!/usr/bin/env python3
"""Migration: Tagging architecture — needs_review/source on lookups, source_hierarchy/dokumenttyp on entries.

Usage:
    python scripts/migrate_tagging_architecture.py
    python scripts/migrate_tagging_architecture.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings


def column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchone()
    return row is not None


def run_migration(db: Session, dry_run: bool = False) -> None:
    steps: list[tuple[str, str]] = []

    for table in ("fachgebiete", "diagnosen", "symptome"):
        if not column_exists(db, table, "needs_review"):
            steps.append(
                (
                    f"add_{table}_needs_review",
                    f"ALTER TABLE {table} ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT FALSE",
                )
            )
        if not column_exists(db, table, "source"):
            steps.append(
                (
                    f"add_{table}_source",
                    f"ALTER TABLE {table} ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'seed'",
                )
            )

    if not column_exists(db, "knowledge_entries", "source_hierarchy"):
        steps.append(
            (
                "add_source_hierarchy",
                "ALTER TABLE knowledge_entries ADD COLUMN source_hierarchy JSONB NOT NULL DEFAULT '[]'::jsonb",
            )
        )
    if not column_exists(db, "knowledge_entries", "dokumenttyp"):
        steps.append(
            (
                "add_dokumenttyp",
                "ALTER TABLE knowledge_entries ADD COLUMN dokumenttyp VARCHAR(50)",
            )
        )

    backfill = [
        (
            "backfill_needs_review",
            """
            UPDATE fachgebiete SET needs_review = TRUE, source = 'folder'
            WHERE beschreibung LIKE '%[AUTO-CREATED]%' AND source = 'seed'
            """,
        ),
        (
            "backfill_diagnose_review",
            """
            UPDATE diagnosen SET needs_review = TRUE, source = 'llm'
            WHERE beschreibung LIKE '%[AUTO-CREATED]%' AND source = 'seed'
            """,
        ),
        (
            "backfill_symptom_review",
            """
            UPDATE symptome SET needs_review = TRUE, source = 'llm'
            WHERE beschreibung LIKE '%[AUTO-CREATED]%' AND source = 'seed'
            """,
        ),
    ]

    view_sql = """
    DROP VIEW IF EXISTS v_entry_search CASCADE;

    CREATE VIEW v_entry_search AS
    SELECT
        ke.id AS entry_id,
        ke.titel,
        ke.zusammenfassung,
        ke.inhalt,
        ke.schwierigkeit,
        ke.unterkategorie,
        ke.dokumenttyp,
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
        COALESCE(
            string_agg(DISTINCT f.name, ' ') FILTER (WHERE f.name IS NOT NULL), ''
        ) || ' ' || COALESCE(
            (SELECT string_agg(elem, ' ')
             FROM jsonb_array_elements_text(ke.source_hierarchy) AS elem),
            ''
        ) AS fachgebiete_text,
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
                (SELECT string_agg(elem, ' ')
                 FROM jsonb_array_elements_text(ke.source_hierarchy) AS elem), ''
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
        ke.id, ke.titel, ke.zusammenfassung, ke.inhalt,
        ke.schwierigkeit, ke.unterkategorie, ke.dokumenttyp, ke.status,
        ke.search_vector, ke.source_hierarchy, ke.created_at, ke.updated_at
    """

    if dry_run:
        print("[DRY RUN] Would execute:")
        for name, sql in steps:
            print(f"  -- {name}\n  {sql.strip()}\n")
        for name, sql in backfill:
            print(f"  -- {name}\n  {sql.strip()}\n")
        print("  -- recreate v_entry_search")
        return

    for name, sql in steps:
        print(f"Running {name}...")
        db.execute(text(sql))

    db.commit()

    for name, sql in backfill:
        print(f"Running {name}...")
        db.execute(text(sql))

    print("Recreating v_entry_search view...")
    db.execute(text(view_sql))
    db.commit()
    print("Migration complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tagging architecture migration")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)
    with Session(engine) as db:
        run_migration(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
