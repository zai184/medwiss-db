# Quickstart Guide

## Quick Start (One Command)

If you have all prerequisites installed, simply run:

```bash
./start.sh
```

This script will:
- Start PostgreSQL with Docker
- Initialize the database (if needed)
- Install Python dependencies
- Start the FastAPI backend
- Install frontend dependencies with bun
- Start the SvelteKit frontend

Then open http://localhost:5175 in your browser!

---

## Manual Setup

Follow the steps below if you prefer to start services manually or the script doesn't work.

## Prerequisites

- **Docker** & **Docker Compose** v2+
- **Python** 3.11+
- **bun** (JavaScript runtime & package manager)
- **Git**

### Install bun
```bash
curl -fsSL https://bun.sh/install | bash
```

## 1. Clone & Setup Environment

```bash
# Navigate to project
cd medwiss-db
```

Every setting has a working default — add a `.env` only to override values
(`DATABASE_URL`, `LLAMASERVER_URL`, `OCR_BACKENDS`, …). There is no
`.env.example` to copy.

## 2. Start Infrastructure

```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Wait for database to be ready (~10s)
docker-compose ps
```

## 3. Initialize Database

```bash
# Option A: Automated setup
python scripts/init_db.py

# Option B: Manual
docker-compose exec -T db psql -U medwiss -d medwiss < database/seeds.sql
```

## 4. Start Backend API

```bash
# Install dependencies (uv.lock is the source of truth)
uv sync

# Start FastAPI server (loopback only — no app auth, trusted network only)
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```


API available at: http://localhost:8000  
API docs: http://localhost:8000/docs

## 5. Start Frontend (Development)

```bash
cd ui

# Install dependencies
bun install

# Start dev server
bun run dev
```

UI available at: http://localhost:5175

## 6. Generate Embeddings (Optional)

For hybrid search, generate vector embeddings:

```bash
cd medwiss-db
source .venv/bin/activate

# Preview what will be processed
python scripts/generate_embeddings.py --dry-run

# Generate embeddings
python scripts/generate_embeddings.py
```

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | test123 | Admin |
| arzt1 | test123 | Editor |
| arztin1 | test123 | Editor |
| pfleger1 | test123 | Viewer |

## Common Commands

```bash
# After Pydantic / route shape changes (same commit)
./scripts/gen-api.sh

# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123"}'

# Search (requires token)
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8000/api/v1/search?type=fts&q=Atemnot"

# Stop everything
docker-compose down

# Reset database
docker-compose down -v
docker-compose up -d
python scripts/init_db.py
```

## Troubleshooting

### PostgreSQL won't start
```bash
docker-compose logs db
```

### Referenz page: Request failed with status code 404
`GET /api/v1/references` must be mounted in `api/main.py` (`include_router(references.router, …)`). `medlinks.txt` lives at `~/Dokumente/Medizin/md/medlinks.txt`. Restart uvicorn after mounting.

### Connection refused
```bash
# Check if PostgreSQL is healthy
docker-compose ps

# Wait for health check
sleep 10
```

### API import errors
```bash
uv sync
```

### UI build fails
```bash
cd ui
rm -rf node_modules bun.lockb
bun install
```
