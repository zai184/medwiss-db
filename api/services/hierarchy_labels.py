"""Extract and apply folder-hierarchy labels for knowledge entries.

Each subfolder under a configured source root (up to 4 levels) becomes a
Fachgebiet tag. The deepest subfolder name is stored as unterkategorie.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import (
    SourceConfig,
    _resolve_content_path,
    load_sources,
)
from database.models import Fachgebiet, KnowledgeEntry

logger = logging.getLogger(__name__)

MAX_HIERARCHY_DEPTH = 4

# Society/org prefixes on AWMF-style folder names (e.g. DRG_Radiologie → Radiologie)
_ORG_PREFIX = re.compile(r"^[A-Z]{2,6}_(.+)$")
# AWMF register numbers (e.g. 038-013_Demenzen → Demenzen)
_AWMF_REGISTER_PREFIX = re.compile(r"^\d{3}-\d{3}[a-z]?_(.+)$", re.IGNORECASE)
# Generic numbered guideline folders (e.g. 001-005_Topic → Topic)
_NUMBERED_PREFIX = re.compile(r"^\d{3}-\d{3}_(.+)$")

CATEGORY_LABELS = {
    "sop": "SOP",
    "notfall": "Notfall",
    "leitlinien": "Leitlinie",
    "studien": "Studie",
    "faecher": "Fachgebiet",
    "pharma": "Pharma",
    "frageboegen": "Fragebogen",
    "infoblaetter": "Infoblatt",
    "red_flags": "Red Flags",
    "pruefungen": "Prüfung",
    "fortbildung": "Fortbildung",
    "nachschlagen": "Nachschlagen",
    "faelle": "Fall",
}


def dokumenttyp_from_category(category: str) -> str:
    """Map source category slug to human-readable dokumenttyp."""
    if not category:
        return ""
    return CATEGORY_LABELS.get(category.strip().lower(), category.replace("_", " ").strip())


def humanize_folder_label(raw: str) -> str:
    """Turn a raw folder name into a readable label.

    Strips organization prefixes (DRG_, DEGAM_, …) and AWMF register IDs,
    then replaces underscores/hyphens with spaces.
    """
    if not raw or not raw.strip():
        return raw

    name = raw.strip()

    for pattern in (_ORG_PREFIX, _AWMF_REGISTER_PREFIX, _NUMBERED_PREFIX):
        match = pattern.match(name)
        if match:
            name = match.group(1)
            break

    name = name.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", name).strip()


def _raw_folder_parts(
    file_path: Path,
    source_root: Path,
    max_depth: int = MAX_HIERARCHY_DEPTH,
) -> list[str]:
    relative = file_path.relative_to(source_root)
    folder_parts = list(relative.parent.parts) if relative.parent != Path(".") else []
    return folder_parts[:max_depth]

def find_source_for_file(
    file_path: Path | str,
) -> Optional[tuple[SourceConfig, Path]]:
    """Find the source config and root path that contains a file."""
    file_path = Path(file_path).resolve()

    best: Optional[tuple[SourceConfig, Path]] = None
    best_root_len = -1

    for source in load_sources():
        path_strings = [source.path]
        if source.additional_paths:
            path_strings.extend(source.additional_paths)

        for path_str in path_strings:
            root = _resolve_content_path(path_str)
            try:
                file_path.relative_to(root)
            except ValueError:
                continue

            if len(root.parts) > best_root_len:
                best = (source, root)
                best_root_len = len(root.parts)

    return best


def extract_hierarchical_labels(
    file_path: Path | str,
    source: SourceConfig,
    source_root: Path,
    max_depth: int = MAX_HIERARCHY_DEPTH,
) -> tuple[list[str], str]:
    """Extract Fachgebiet labels and unterkategorie from a file's folder path."""
    file_path = Path(file_path).resolve()
    source_root = source_root.resolve()

    raw_labels = _raw_folder_parts(file_path, source_root, max_depth)
    labels = [humanize_folder_label(part) for part in raw_labels]
    # Preserve order while dropping empty/duplicate consecutive labels
    deduped: list[str] = []
    for label in labels:
        if label and (not deduped or deduped[-1] != label):
            deduped.append(label)
    labels = deduped

    if labels:
        unterkategorie = labels[-1]
    else:
        unterkategorie = CATEGORY_LABELS.get(source.category, source.category)

    return labels, unterkategorie


def remove_stale_folder_tags(entry: KnowledgeEntry, raw_folder_parts: list[str]) -> int:
    """Remove old raw-prefixed folder tags before re-applying humanized labels."""
    if not raw_folder_parts:
        return 0

    raw_set = set(raw_folder_parts)
    humanized_set = {humanize_folder_label(part) for part in raw_folder_parts}
    removed = 0
    for fach in list(entry.fachgebiete):
        if fach.name in raw_set or fach.name in humanized_set:
            entry.fachgebiete.remove(fach)
            removed += 1

    return removed


def apply_hierarchy_labels(
    db: Session,
    entry: KnowledgeEntry,
    file_path: Path | str,
    source: SourceConfig,
    source_root: Path,
    *,
    replace_stale_tags: bool = False,
) -> int:
    """Apply folder-hierarchy labels to entry metadata. Returns count of new hierarchy labels."""
    file_path = Path(file_path).resolve()
    source_root = source_root.resolve()

    raw_parts = _raw_folder_parts(file_path, source_root)
    if replace_stale_tags:
        remove_stale_folder_tags(entry, raw_parts)
        entry.source_hierarchy = []

    from api.services.tagging_service import TaggingService

    service = TaggingService(db)
    result = service.apply_folder_hierarchy(
        entry, file_path, source, source_root, merge=not replace_stale_tags
    )
    return result.hierarchy_added


def consolidate_fachgebiet_aliases(db: Session) -> dict[str, int]:
    """Rename or merge prefixed Fachgebiet records into humanized names."""
    stats = {"renamed": 0, "merged": 0, "links_moved": 0}
    fachgebiete = db.query(Fachgebiet).all()
    by_name = {f.name: f for f in fachgebiete}

    for fach in list(fachgebiete):
        humanized = humanize_folder_label(fach.name)
        if humanized == fach.name:
            continue

        target = by_name.get(humanized)
        if target is None:
            fach.name = humanized
            by_name[humanized] = fach
            stats["renamed"] += 1
            continue

        if target.id == fach.id:
            continue

        entries = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.fachgebiete.any(Fachgebiet.id == fach.id))
            .all()
        )
        for entry in entries:
            if target not in entry.fachgebiete:
                entry.fachgebiete.append(target)
                stats["links_moved"] += 1
            if fach in entry.fachgebiete:
                entry.fachgebiete.remove(fach)

        db.delete(fach)
        del by_name[fach.name]
        stats["merged"] += 1

    db.flush()
    return stats


def _lookup_fachgebiet_by_label(db: Session, label: str) -> Optional[Fachgebiet]:
    """Find an existing Fachgebiet by humanized label (case-insensitive)."""
    normalized = label.strip().lower()
    if not normalized:
        return None
    return (
        db.query(Fachgebiet)
        .filter(func.lower(Fachgebiet.name) == normalized)
        .first()
    )


def extract_tag_suggestions_for_entry(
    db: Session,
    entry: KnowledgeEntry,
) -> dict:
    """Return folder-based tag suggestions without mutating the entry."""
    from api.services.tagging_service import TaggingService

    return TaggingService(db).get_suggestions(entry)


def apply_folder_suggestions(db: Session, entry: KnowledgeEntry) -> int:
    """Apply missing folder hierarchy labels to entry metadata."""
    from api.services.tagging_service import TaggingService

    service = TaggingService(db)
    result = service.apply_folder_for_entry(entry, merge=True)
    db.commit()
    return result.hierarchy_added


def apply_hierarchy_labels_for_path(
    db: Session,
    entry: KnowledgeEntry,
    *,
    replace_stale_tags: bool = False,
) -> int:
    """Resolve source from entry.source_path and apply hierarchy labels."""
    if not entry.source_path:
        return 0

    match = find_source_for_file(entry.source_path)
    if not match:
        logger.debug("No source match for entry %s path %s", entry.id, entry.source_path)
        return 0

    source, source_root = match
    return apply_hierarchy_labels(
        db,
        entry,
        entry.source_path,
        source,
        source_root,
        replace_stale_tags=replace_stale_tags,
    )
