# config/ - Source Folder Configuration

> Source folder definitions and Pydantic models for batch import pipeline.

## WHERE TO LOOK

| File | Purpose |
|------|---------|
| `__init__.py` | `SourceConfig` / `SourcesConfig` Pydantic models, `load_sources()` loader, path resolution helpers |
| `sources.yaml` | 11 source folder definitions: paths, categories, default fachgebiete, file types, auto_classify flags |

## KEY CONCEPTS

- **SourceConfig**: One entry per source folder. Fields: `name`, `path`, `category`, `default_fachgebiete`, `auto_classify`, `file_types`, `additional_paths` (for aggregated sources like Fortbildung).
- **Path resolution**: Relative to `WORKSPACE_ROOT` (env var) or `medwiss-db/` parent. `SOURCES_PATH` env var overrides base path.
- **Validation**: `load_sources(validate_exists=True)` skips missing folders silently.

## CONVENTIONS

- Folder names use numbered prefixes (`1_SOPs`, `2_Leitlinien`, ... `10_Pharma`) plus `Fortbildung`.
- Categories are lowercase with underscores (`sop`, `leitlinien`, `red_flags`, `frageboegen`, etc.).
- `additional_paths` is only used for Fortbildung (aggregates 2024, 2025, 2026 folders).
- Add new sources to `sources.yaml` only. `__init__.py` is schema + loader, no hardcoded data.
