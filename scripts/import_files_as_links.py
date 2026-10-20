"""Link-only import - Create database entries for files without OCR/text extraction.

This script creates knowledge_entries with source_path pointing to files,
without processing through OCR/LLM pipeline. Much faster for
file-first architecture where files are the source of truth.

Usage:
    python scripts/import_files_as_links.py [--folder FOLDER_NAME]

Examples:
    python scripts/import_files_as_links.py                    # Import all folders
    python scripts/import_files_as_links.py --folder 1_SOPs    # Import specific folder
"""

import sys
from pathlib import Path
from typing import Optional
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from api.database import SessionLocal
from api.services.hierarchy_labels import CATEGORY_LABELS
from database.models import KnowledgeEntry, User
from config import load_sources
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_admin_user(db: Session) -> Optional[User]:
    """Get the admin user for created_by field."""
    return db.query(User).filter(User.role == "admin").first()


def get_category_from_folder(folder_name: str) -> str:
    """Map folder name to category."""
    mapping = {
        "1_SOPs": "sop",
        "2_Leitlinien": "richtlinien",
        "3_Studien": "studie",
        "4_Red Flags": "redflag",
        "5_Fragebögen": "fragebogen",
        "6_Nachschlagen": "nachschlagen",
        "7_Infoblätter": "infoblatt",
        "8_Fächer": "fach",
        "9_Fälle": "fall",
        "10_Pharma": "pharma",
        "Fortbildung": "fortbildung",
    }
    return mapping.get(folder_name, "unbekannt")


def create_entry_from_file(
    db: Session, file_path: Path, source_config, admin_user: User, base_path: Path
) -> bool:
    """Create a knowledge entry for a file without OCR.

    Args:
        db: Database session
        file_path: Path to the file
        source_config: Source configuration
        admin_user: Admin user for created_by
        base_path: Base path to resolve relative paths

    Returns:
        True if entry created, False if skipped (already exists)
    """
    # Resolve to absolute path if relative
    if not file_path.is_absolute():
        file_path = base_path / file_path
    file_path = file_path.resolve()

    # Check if entry already exists for this file
    existing = db.query(KnowledgeEntry).filter(KnowledgeEntry.source_path == str(file_path)).first()

    if existing:
        logger.debug(f"Skipping existing file: {file_path}")
        return False

    # Create entry
    filename = file_path.stem
    category = get_category_from_folder(source_config.name)

    entry = KnowledgeEntry(
        titel=filename,
        zusammenfassung=f"Dokument aus {source_config.name}",
        inhalt=f"# {filename}\n\nQuelle: {source_config.name}\nPfad: {file_path}",
        quelle=source_config.name,
        dokumenttyp=CATEGORY_LABELS.get(category, category),
        schwierigkeit="grundlegend",
        source_path=str(file_path),
        status="freigegeben",
        version=1,
        created_by=admin_user.id if admin_user else None,
    )

    db.add(entry)
    db.commit()
    logger.info(f"Created entry for: {file_path}")
    return True


def import_folder(db: Session, source_config, admin_user: User, base_path: Path) -> tuple[int, int]:
    """Import all files from a folder.

    Returns:
        (imported_count, skipped_count)
    """
    imported = 0
    skipped = 0

    if not base_path.exists():
        logger.warning(f"Folder does not exist: {base_path}")
        return imported, skipped

    # Supported extensions
    extensions = {".pdf", ".md", ".txt", ".jpg", ".jpeg", ".png", ".mp3", ".wav", ".m4a"}

    # Find all files recursively
    for file_path in base_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            try:
                if create_entry_from_file(db, file_path, source_config, admin_user, base_path):
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error importing {file_path}: {e}")
                db.rollback()

    return imported, skipped


def main():
    parser = argparse.ArgumentParser(description="Import files as links only (no OCR)")
    parser.add_argument("--folder", type=str, help="Specific folder to import (e.g., 1_SOPs)")
    args = parser.parse_args()

    logger.info("Starting link-only import...")

    db = SessionLocal()
    try:
        # Attribution user (optional — no auth in this project)
        admin_user = get_admin_user(db)
        if admin_user:
            logger.info(f"Using admin user: {admin_user.username}")
        else:
            logger.info("No user rows found; entries will have no created_by attribution.")

        # Load source configurations
        sources = load_sources()

        total_imported = 0
        total_skipped = 0

        for source in sources:
            # Skip if specific folder requested
            if args.folder and source.name != args.folder:
                continue

            logger.info(f"\nProcessing source: {source.name}")

            # Import main path
            main_path = Path(source.path)
            if main_path.exists():
                imported, skipped = import_folder(db, source, admin_user, main_path)
                total_imported += imported
                total_skipped += skipped
                logger.info(f"  Main path: {imported} imported, {skipped} skipped")

            # Import additional paths (for Fortbildung)
            if source.additional_paths:
                for add_path_str in source.additional_paths:
                    add_path = Path(add_path_str)
                    if add_path.exists():
                        imported, skipped = import_folder(db, source, admin_user, add_path)
                        total_imported += imported
                        total_skipped += skipped
                        logger.info(f"  Additional path: {imported} imported, {skipped} skipped")

        logger.info(f"\n{'=' * 50}")
        logger.info("Import complete!")
        logger.info(f"Total imported: {total_imported}")
        logger.info(f"Total skipped (already exist): {total_skipped}")
        logger.info(f"{'=' * 50}")

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
