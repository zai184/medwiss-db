# API MODULE

**Parent:** [../AGENTS.md](../AGENTS.md) | **App:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW
FastAPI REST API for the Medical Knowledge Database.

## STRUCTURE

```
api/
├── main.py              # App factory, CORS, router registration
├── config.py            # Pydantic settings
├── database.py            # SQLAlchemy engine & session
├── models.py            # Pydantic request/response models
└── routers/
    ├── entries.py       # CRUD + tag-suggestions
    ├── classifications.py # /fachgebiete, /diagnosen, /symptome, /dokumenttypen, /ordner-labels, resolve-labels, pending-review
    ├── search.py        # /search keyword+filters, /search/chunks, /search/chunks/rag
    ├── stats.py         # /stats/overview, /by-category, /by-fach, /by-diagnose, /recent
    ├── pipeline.py      # /pipeline/process-file (single file)
    ├── files.py         # /files view/download/info, /files/sync, admin sync-status
    ├── summarize.py     # /entries/{id}/summarize, /entries/{id}/transcribe
    ├── sources.py       # /sources (configured folder list)
    ├── admin.py         # /admin/classify-from-filename (regex classification)
    ├── icd11.py         # /icd11/token (WHO OAuth2 proxy)
    ├── references.py    # /references (live medlinks.txt parse)
    └── pubmed.py        # /pubmed/search
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add new endpoint | `routers/*.py` | Follow existing router pattern |
| Database models | `database.py` | SQLAlchemy models from `database/models.py` |
| API configuration | `config.py` | Environment-based settings |
| Request/response schemas | `models.py` | Pydantic models |

## CONVENTIONS

- Routers use `prefix="/api/v1"` from main.py
- All routes return Pydantic models, not raw dicts
- After changing Pydantic models or route shapes: `./scripts/gen-api.sh` (same commit)
- Database sessions via FastAPI dependency injection

## ANTI-PATTERNS

- **NEVER** hardcode URLs - use `config.settings`
- **NEVER** return SQLAlchemy objects directly - convert to Pydantic
- **NEVER** commit in routers - use `db.commit()` in service layer or context manager
