# API MODULE

**Parent:** [../AGENTS.md](../AGENTS.md) | **App:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW
FastAPI REST API for the Medical Knowledge Database.

## STRUCTURE

```
api/
├── main.py              # App factory, CORS, router registration
├── config.py            # Pydantic settings
├── database.py          # SQLAlchemy engine & session
├── dependencies.py      # JWT auth dependencies
├── models.py            # Pydantic request/response models
└── routers/
    ├── auth.py          # POST /auth/login, /auth/register, /auth/me
    ├── entries.py       # CRUD for knowledge entries
    ├── classifications.py # /fachgebiete, /diagnosen, /symptome
    ├── search.py        # /search?type=fts|faceted|hybrid
    └── stats.py         # /stats/overview, /stats/by-fach
```

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add new endpoint | `routers/*.py` | Follow existing router pattern |
| Auth requirements | `dependencies.py` | `get_current_user()`, `require_role()` |
| Database models | `database.py` | SQLAlchemy models from `database/models.py` |
| API configuration | `config.py` | Environment-based settings |
| Request/response schemas | `models.py` | Pydantic models |

## CONVENTIONS

- Routers use `prefix="/api/v1"` from main.py
- Auth: JWT in `Authorization: Bearer <token>` header
- All routes return Pydantic models, not raw dicts
- After changing Pydantic models or route shapes: `./scripts/gen-api.sh` (same commit)
- Database sessions via FastAPI dependency injection

## ANTI-PATTERNS

- **NEVER** hardcode URLs - use `config.settings`
- **NEVER** return SQLAlchemy objects directly - convert to Pydantic
- **NEVER** commit in routers - use `db.commit()` in service layer or context manager
