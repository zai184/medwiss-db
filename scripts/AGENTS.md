# scripts/ - CLI Tools & Utilities

**OVERVIEW:** Standalone CLI scripts for batch operations, pipeline execution, and manual testing. All scripts run outside the FastAPI server process.

## WHERE TO LOOK

| Script | Purpose | Key Pattern |
|--------|---------|-------------|
| `run_pipeline.py` | Manual AI pipeline execution | Direct `pipeline.orchestrator` imports; outputs to `pipeline/output/` |
| `generate_embeddings.py` | Batch embedding generation | Direct SQLAlchemy + `pipeline.embeddings`; requires running llamaserver; commits in batches |
| `import_files_as_links.py` | Fast link-only import (no OCR) | Direct DB access via `SessionLocal`; skips existing by `source_path`; maps folder names to categories |
| `test_*.py` | Manual integration tests | Not pytest. Run directly with `python scripts/test_*.py`. Use `get_db_context()` context manager |
| `gen-api.sh` / `export_openapi.py` | Dump FastAPI OpenAPI → `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts` | Exception: imports `api.main:app`. Run after Pydantic / route shape changes, same commit |

## CONVENTIONS

- **Path hack:** Every script starts with `sys.path.insert(0, str(Path(__file__).parent.parent))` to import project modules
- **API scripts** talk to `localhost:8000/api/v1`. Server must be running
- **DB scripts** (`generate_embeddings.py`, `import_files_as_links.py`, `test_*.py`) connect directly to PostgreSQL via `api.database` or `api.config.settings`
- **Logging:** Use `logging.basicConfig(...)` or `rich.console.Console`. No shared logging config
- **Exit codes:** Return `0` success, `1` error, `130` keyboard interrupt

## ANTI-PATTERNS

- **Do not** add pytest tests here. This directory is for runnable CLI tools and manual tests only
- **Do not** import from `api.routers` or `api.main` in scripts (exception: `export_openapi.py` dumps `api.main:app`). Use `api.services`, `pipeline.*`, or direct DB access
- **Do not** hardcode paths. Resolve relative to `Path(__file__).parent.parent` (workspace root)
- **Do not** run `generate_embeddings.py` without checking llamaserver health first. Script exits hard if unreachable
