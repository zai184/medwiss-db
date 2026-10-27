# config/ - Source Folder Configuration

> Source folder registry: dynamic discovery + YAML overrides, Pydantic models, content-root path resolution.

## WHERE TO LOOK

| File | Purpose |
|------|---------|
| `__init__.py` | `SourceConfig` / `SourcesConfig` Pydantic models, `load_sources()` loader, path resolution helpers |
| `discover_sources.py` | Dynamic discovery: every `NN_*` folder under the content root plus `Fortbildung YYYY`; derives category/description/file-type defaults |
| `sources.yaml` | 11 override entries: categories, default fachgebiete, file types, `additional_paths` — merged **over** discovery by name |

## KEY CONCEPTS

- **load_sources() = discovery ∪ yaml**: discovered folders are the base, yaml entries override them by name (and yaml-only entries are added even if the folder is missing). The watcher's path list comes from here — a new `NN_*` folder on disk is watched without touching yaml.
- **SourceConfig**: One entry per source folder. Fields: `name`, `path`, `category`, `default_fachgebiete`, `auto_classify`, `file_types`, `additional_paths` (for aggregated sources like Fortbildung).
- **Content root**: Source paths resolve against `MEDWISS_CONTENT_ROOT` (default `~/Dokumente/Medizin`; VPS: `/srv/medwiss/corpus`). Read-only to the app.
- **Workspace root**: `WORKSPACE_ROOT` env var, else the repo's parent directory.
- **Validation**: `load_sources(validate_exists=False)` by default — no disk check unless asked for.

## CONVENTIONS

- Folder names use numbered prefixes (`1_SOPs` … `10_Bücher`) plus `Fortbildung` and `Fortbildungen`.
- Categories are lowercase with underscores (`sop`, `notfall`, `leitlinien`, `red_flags`, `frageboegen`, etc.).
- `additional_paths` is only used for Fortbildung (aggregates 2024, 2025, 2026 folders).
- Add stable overrides (defaults, categories, file types) to `sources.yaml` only; `__init__.py` is schema + loader, no hardcoded data. New plain folders need nothing.
