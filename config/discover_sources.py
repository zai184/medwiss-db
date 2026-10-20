"""Dynamic source folder discovery."""

import os
import re
from pathlib import Path

def _get_content_root() -> Path:
    """Canonical content root (mirror of config.get_content_root; kept local
    to avoid a circular import)."""
    env_root = os.environ.get("MEDWISS_CONTENT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return (Path.home() / "Dokumente" / "Medizin").resolve()


def _resolve_source_path(path: str, content_root: Path) -> Path:
    """Resolve a source path against the content root (absolute passes through)."""
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    parts = [part for part in p.parts if part not in ("..", ".")]
    return content_root.joinpath(*parts).resolve()


def discover_subcategories(source_path: str) -> list[str]:
    """Discover immediate subfolder names of a source folder.

    Args:
        source_path: Relative path to the source folder (e.g., '../1_SOPs').

    Returns:
        List of subfolder names (e.g., ['SOPs Notaufnahme', 'SOPs GRC']).
        Hidden folders (starting with '.') are excluded.
    """
    resolved = _resolve_source_path(source_path, _get_content_root())

    if not resolved.is_dir():
        return []

    subcategories = []
    for entry in sorted(resolved.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            subcategories.append(entry.name)

    return subcategories


def _derive_category(folder_name: str) -> str:
    name = re.sub(r'^\d+_', '', folder_name)
    name = re.sub(r'\s+\d{4}$', '', name)
    name = name.lower()
    name = name.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    name = name.replace(' ', '_')
    # Normalize plural forms
    if name.endswith('s') and name not in ['flags', 'red_flags']:
        name = name[:-1]
    return name


def _derive_description(folder_name: str) -> str:
    name = re.sub(r'^\d+_', '', folder_name)
    name = re.sub(r'\s+\d{4}$', '', name)
    return name


def _get_default_file_types(category: str) -> list[str]:
    defaults = {
        'sop': ['.pdf', '.jpg', '.png', '.md'],
        'leitlinien': ['.pdf', '.md'],
        'studien': ['.pdf', '.md'],
        'faecher': ['.pdf', '.jpg', '.png', '.md'],
        'pharma': ['.pdf', '.md'],
        'frageboegen': ['.pdf', '.docx', '.md'],
        'infoblaetter': ['.pdf', '.jpg', '.png', '.md'],
        'pruefungen': ['.pdf', '.md'],
        'flags': ['.pdf', '.jpg', '.png', '.md'],
        'fortbildung': ['.pdf', '.mp3', '.wav', '.m4a', '.jpg', '.png', '.md'],
    }
    return defaults.get(category, ['.pdf', '.md'])


def discover_sources() -> list[dict]:
    """Discover source folders dynamically from the filesystem.

    Returns:
        List of dicts with keys: name, path, category, description,
        auto_classify, file_types, additional_paths, subcategories.
    """
    content_root = _get_content_root()
    parent_dir = content_root

    candidates = []

    for item in sorted(parent_dir.iterdir()):
        if not item.is_dir():
            continue

        folder_name = item.name
        if folder_name == content_root.name or folder_name.startswith('.'):
            continue

        is_source = (
            re.match(r'^\d+_', folder_name)
            or folder_name in ['Flags', 'Red Flags']
            or folder_name == 'Fortbildung'
        )

        if not is_source:
            continue

        if re.match(r'^Fortbildung\s+\d{4}$', folder_name):
            continue

        category = _derive_category(folder_name)
        is_numbered = re.match(r'^\d+_', folder_name) is not None
        candidates.append((folder_name, category, is_numbered))

    discovered = []
    seen_categories = set()

    for folder_name, category, is_numbered in sorted(candidates, key=lambda x: (x[2], x[0])):
        if category in seen_categories:
            continue
        seen_categories.add(category)

        source_path = folder_name
        discovered.append({
            'name': folder_name,
            'path': source_path,
            'category': category,
            'description': _derive_description(folder_name),
            'auto_classify': True,
            'file_types': _get_default_file_types(category),
            'subcategories': discover_subcategories(source_path),
        })

    fortbildung_years = []
    for item in sorted(parent_dir.iterdir()):
        if item.is_dir() and re.match(r'^Fortbildung\s+\d{4}$', item.name):
            fortbildung_years.append(item.name)

    if fortbildung_years:
        fortbildung_path = fortbildung_years[0]
        discovered.append({
            'name': 'Fortbildung',
            'path': fortbildung_path,
            'category': 'fortbildung',
            'description': 'Continuing medical education materials',
            'auto_classify': True,
            'file_types': ['.pdf', '.mp3', '.wav', '.m4a', '.jpg', '.png', '.md'],
            'additional_paths': list(fortbildung_years[1:]),
            'subcategories': discover_subcategories(fortbildung_path),
        })

    return discovered
