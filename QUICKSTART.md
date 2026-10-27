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
- **uv** (Python package manager)
- **bun** (JavaScript runtime & package manager)
- **Git**

### Install bun
```bash
curl -fsSL https://bun.sh/install | bash
```

### Install uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
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

The schema is applied automatically by the container on first start
(`docker-compose.yml` mounts `database/schema.sql`). Seed lookup tables and
test entries once with:

```bash
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

## Common Commands

```bash
# After Pydantic / route shape changes (same commit)
./scripts/gen-api.sh

# Health check
curl http://localhost:8000/health

# Search (no authentication — auth was removed 2026-08-29)
curl "http://localhost:8000/api/v1/search?q=Atemnot"

# Stop everything
docker-compose down

# Reset database (schema re-applies on first container start; then re-seed)
docker-compose down -v
docker-compose up -d
docker-compose exec -T db psql -U medwiss -d medwiss < database/seeds.sql
```

## Troubleshooting

### PostgreSQL won't start
```bash
docker-compose logs db
```

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
rm -rf node_modules bun.lock
bun install
```
