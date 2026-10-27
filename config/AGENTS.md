# config/ - Source Folder Configuration

> Source folder registry: definitions, Pydantic models, content-root path resolution.

## WHERE TO LOOK

| File | Purpose |
|------|---------|
| `__init__.py` | `SourceConfig` / `SourcesConfig` Pydantic models, `load_sources()` loader, path resolution helpers |
| `sources.yaml` | 11 source folder definitions: paths, categories, default fachgebiete, file types, auto_classify flags |

## KEY CONCEPTS

- **SourceConfig**: One entry per source folder. Fields: `name`, `path`, `category`, `default_fachgebiete`, `auto_classify`, `file_types`, `additional_paths` (for aggregated sources like Fortbildung).
- **Content root**: Source paths resolve against `MEDWISS_CONTENT_ROOT` (default `~/Dokumente/Medizin`; VPS: `/srv/medwiss/corpus`). Read-only to the app.
- **Workspace root**: `WORKSPACE_ROOT` env var, else the repo's parent directory.
- **Validation**: `load_sources(validate_exists=False)` by default — no disk check unless asked for.

## CONVENTIONS

- Folder names use numbered prefixes (`1_SOPs` … `9_Prüfungen`) plus `Fortbildung` and `Fortbildungen`.
- Categories are lowercase with underscores (`sop`, `notfall`, `leitlinien`, `red_flags`, `frageboegen`, etc.).
- `additional_paths` is only used for Fortbildung (aggregates 2024, 2025, 2026 folders).
- Add new sources to `sources.yaml` only. `__init__.py` is schema + loader, no hardcoded data.
