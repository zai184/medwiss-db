"""Configuration system for the Medical Knowledge Database.

Merges environment settings (from api.config.Settings) with source folder
definitions (from sources.yaml + filesystem discovery).

Import from here to get both:
    from config import settings, load_sources, SourceConfig
"""

from api.config import settings, Settings  # noqa: F401 — re-export for single import point
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from config.discover_sources import discover_sources as _discover_sources


class SourceConfig(BaseModel):
    """Configuration for a single source folder."""

    name: str = Field(..., description="Display name of the source")
    path: str = Field(..., description="Path relative to the content root")
    category: str = Field(..., description="Category for imported entries")
    description: str = Field(default="", description="Human-readable description")
    default_fachgebiete: list[str] = Field(default_factory=list, description="Default fachgebiete")
    auto_classify: bool = Field(default=True, description="Enable AI classification")
    file_types: list[str] = Field(
        default_factory=lambda: [".pdf", ".jpg", ".png", ".md"],
        description="Supported file extensions",
    )
    additional_paths: Optional[list[str]] = Field(
        default=None,
        description="Additional paths for aggregated sources like Fortbildung",
    )
    subcategories: list[str] = Field(
        default_factory=list,
        description="Subfolder names within the source folder",
    )


class SourcesConfig(BaseModel):
    """Root configuration model."""

    sources: list[SourceConfig] = Field(
        default_factory=list, description="List of source configurations"
    )
    env_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variable names for overrides",
    )


def _get_workspace_root() -> Path:
    """Get the workspace root directory (the medwiss-db repo).

    Uses WORKSPACE_ROOT env var if set, otherwise defaults to the directory
    containing this file (medwiss-db/config/).
    """
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)

    return Path(__file__).parent.parent


def get_content_root() -> Path:
    """Canonical content root — the authoritative Medizin tree (read-only to the app).

    MEDWISS_CONTENT_ROOT overrides; default is ~/Dokumente/Medizin.
    On the VPS that path is a symlink to the corpus directory.
    """
    env_root = os.environ.get("MEDWISS_CONTENT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    return (Path.home() / "Dokumente" / "Medizin").resolve()


def _resolve_content_path(path: str) -> Path:
    """Resolve a source-folder path against the content root.

    Absolute paths pass through; relative paths may keep legacy `../`
    prefixes (stripped) and are resolved inside the content root.
    """
    p = Path(path)
    if p.is_absolute():
        return p.resolve()

    parts = [part for part in p.parts if part not in ("..", ".")]
    return get_content_root().joinpath(*parts).resolve()


def _resolve_path(path: str, workspace_root: Path) -> Path:
    """Resolve a relative path to an absolute path.

    Args:
        path: Relative path (e.g., '1_SOPs')
        workspace_root: The workspace root directory

    Returns:
        Absolute Path object
    """
    if Path(path).is_absolute():
        return Path(path)

    return (workspace_root / path).resolve()


def _check_folder_exists(source: SourceConfig, workspace_root: Path) -> bool:
    """Check if a source folder exists (resolved against the content root)."""
    main_path = _resolve_content_path(source.path)
    if main_path.exists() and main_path.is_dir():
        return True

    if source.additional_paths:
        for additional_path in source.additional_paths:
            additional_resolved = _resolve_content_path(additional_path)
            if additional_resolved.exists() and additional_resolved.is_dir():
                return True

    return False


def load_sources(validate_exists: bool = False) -> list[SourceConfig]:
    """Load source configurations with dynamic discovery + YAML override.

    Discovers source folders dynamically from the content root, then merges
    with sources.yaml for custom settings like default_fachgebiete and
    file_types. YAML entries override discovered entries by name.

    Args:
        validate_exists: If True, verify folders exist. If False (default),
                        missing folders don't cause errors.

    Returns:
        List of SourceConfig objects

    Raises:
        FileNotFoundError: If sources.yaml doesn't exist
        ValidationError: If YAML structure doesn't match expected schema
    """
    discovered = _discover_sources()
    discovered_by_name = {s['name']: s for s in discovered}

    try:
        yaml_config = load_yaml_config()
        sources_config = SourcesConfig(**yaml_config)
        yaml_sources = {s.name: s for s in sources_config.sources}
    except FileNotFoundError:
        yaml_sources = {}

    merged = {}

    for name, disc in discovered_by_name.items():
        merged[name] = SourceConfig(
            name=disc['name'],
            path=disc['path'],
            category=disc['category'],
            description=disc['description'],
            auto_classify=disc['auto_classify'],
            file_types=disc['file_types'],
            subcategories=disc.get('subcategories', []),
        )

    for name, yaml_source in yaml_sources.items():
        if name in merged:
            discovered_source = merged[name]
            merged[name] = SourceConfig(
                name=yaml_source.name,
                path=yaml_source.path,
                category=yaml_source.category,
                description=yaml_source.description or discovered_source.description,
                default_fachgebiete=yaml_source.default_fachgebiete or discovered_source.default_fachgebiete,
                auto_classify=yaml_source.auto_classify,
                file_types=yaml_source.file_types or discovered_source.file_types,
                additional_paths=yaml_source.additional_paths or discovered_source.additional_paths,
                subcategories=discovered_source.subcategories,
            )
        else:
            merged[name] = SourceConfig(
                name=yaml_source.name,
                path=yaml_source.path,
                category=yaml_source.category,
                description=yaml_source.description,
                default_fachgebiete=yaml_source.default_fachgebiete,
                auto_classify=yaml_source.auto_classify,
                file_types=yaml_source.file_types,
                additional_paths=yaml_source.additional_paths,
                subcategories=yaml_source.subcategories if yaml_source.subcategories else [],
            )

    loaded_sources = []
    for source in merged.values():
        if validate_exists and not _check_folder_exists(source, _get_workspace_root()):
            continue
        loaded_sources.append(source)

    return loaded_sources


def get_source_by_name(name: str) -> Optional[SourceConfig]:
    """Get a source configuration by name.

    Args:
        name: Source name

    Returns:
        SourceConfig if found, None otherwise
    """
    for source in load_sources():
        if source.name == name:
            return source
    return None


def get_sources_by_category(category: str) -> list[SourceConfig]:
    """Get all sources in a specific category.

    Args:
        category: Category name

    Returns:
        List of SourceConfig objects
    """
    sources = load_sources()
    return [s for s in sources if s.category == category]


def get_all_categories() -> list[str]:
    """Get all unique categories from sources.

    Returns:
        Sorted list of unique category names
    """
    sources = load_sources()
    return sorted(set(s.category for s in sources))


def load_yaml_config() -> dict[str, object]:
    """Load the YAML configuration file."""
    config_path = Path(__file__).parent / "sources.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
