"""Export all unique (folder, filename) pairs to a reviewable text file.

Usage:
    uv run python scripts/export_filenames.py [output_path]

Default output: data/filenames.txt

This is the raw material for building the regex diagnosis library.
Each line shows the relative path (source folder → subfolders → filename).
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from api.database import SessionLocal
from database.models import KnowledgeEntry

# Source roots recognized in the workspace (numbered or named)
SOURCE_ROOT_RE = (
    r"^(\d+_|Fortbildung|Red\s?Flags|Flags)"
)


def relative_path(full_path: str) -> str:
    """Strip the absolute workspace prefix, keep source-root-relative path."""
    parts = full_path.split("/")
    # Find the first source-root segment
    for i, part in enumerate(parts):
        import re

        if re.match(SOURCE_ROOT_RE, part):
            return "/".join(parts[i:])
    return full_path


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/filenames.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    db: Session = SessionLocal()
    rows = db.query(KnowledgeEntry.source_path).filter(
        KnowledgeEntry.source_path.isnot(None),
        KnowledgeEntry.source_path != "",
    ).all()
    db.close()

    # Unique relative paths, sorted
    unique = sorted({relative_path(r[0]) for r in rows})

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# MedWiss Dateinamen & Ordnerpfade (für Diagnose-Klassifikation)\n")
        f.write(f"# {len(unique)} eindeutige Pfade\n")
        f.write("# Format: Ordnerpfad/Dateiname\n")
        f.write("#\n")
        for p in unique:
            f.write(p + "\n")

    print(f"Exported {len(unique)} unique paths to {out_path}")


if __name__ == "__main__":
    main()
