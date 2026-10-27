# Medizinische Wissensdatenbank (Medical Knowledge Database)

A browser for local medical folders. The files under the source folders are the library. PostgreSQL 15 + pgvector is the index: one row per file (path, hash, tags, search), plus guideline passages in `chunks` for Leitlinien search. Rechner and Notfall do not use the database. OCR and summarization run on demand.

> [!WARNING]
> **No authentication.** All API endpoints are public by design — run this only on a
> trusted network (LAN / VPN). Do not expose it to the public internet without putting
> an authenticating proxy in front.
>
> **Your files are the library, and they are not included.** This repository contains
> only the application (AGPL-3.0). The medical corpus under your content root
> (`~/Dokumente/Medizin` by default) stays on your machine and keeps its own licensing.
>
> **Requirements:** PostgreSQL 15 + pgvector. Optional AI features (summarize, RAG,
> embeddings) need a local Llamaserver or an OpenRouter API key.

## Quick Start

### 1. Start Services

```bash
# Start PostgreSQL
docker-compose up -d

# Start API server
uv run uvicorn api.main:app --reload

# In another terminal, start frontend
cd ui && bun run dev
```

### 2. Access the Application

- **API**: http://localhost:8000/docs (Swagger docs)
- **Frontend**: http://localhost:5175

### 3. Note

There is no login (see warning above) — the frontend is ready to use.

## Source Folders

The library is the folder tree under your content root (`~/Dokumente/Medizin` by
default; override with `MEDWISS_CONTENT_ROOT`). There is no import command —
the source watcher and the startup reconcile index the files directly.
Configured folders (`config/sources.yaml`):

| Folder | Category |
|--------|----------|
| 1_SOPs | SOP |
| 2_Notfall | Emergency medicine |
| 3_Leitlinien | Guidelines |
| 4_Red_Flags | Red flags |
| 5_Fächer | Medical specialties |
| 6_Pharmakologie | Pharmacology |
| 7_Fragebögen | Questionnaires |
| 8_Infoblätter | Info sheets |
| 9_Prüfungen | Exams |
| Fortbildung | CME (2024–2026) |
| Fortbildungen | CME platforms (Amboss, GiDi, …) |

## Architecture

```
┌─────────────────────────────────────────┐
│         Frontend (SvelteKit)              │
│   Dashboard │ Search │ Entry │ KI Upload   │
└──────────────────┬────────────────────────┘
                   │ HTTP/REST
┌─────────────────▼────────────────────────┐
│         Backend (FastAPI)                 │
│  CRUD │ Search │ Stats │ Pipeline │ Files │
└──────────────────┬────────────────────────┘
                   │ SQL
┌─────────────────▼────────────────────────┐
│        PostgreSQL 15 + pgvector          │
│   Tables │ FTS (tsvector) │ Vectors     │
└─────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL 15 + pgvector |
| Backend | FastAPI + SQLAlchemy |
| Frontend | SvelteKit + TypeScript |
| OCR | Tesseract / OpenRouter glm-4.6v |
| AI | Llamaserver (local) + OpenRouter |
| Package Manager | bun |

## Project Structure

```
medwiss-db/
├── api/                    # FastAPI application
│   ├── routers/           # API endpoints
│   └── services/          # Business logic
├── database/              # Schema & models
├── pipeline/              # KI processing modules
│   ├── batch_processor.py  # Single-file processing + hashing
│   ├── classification_resolver.py  # Dokumenttyp/Ordner-Label resolution
│   └── duplicate_detector.py     # SHA-256 duplicate detection
├── config/               # Source folder configuration
├── scripts/              # CLI tools
│   └── generate_embeddings.py  # Batch entry embeddings
├── search/               # Search implementations
└── ui/                  # SvelteKit frontend
```

## API Endpoints

### Knowledge Entries
- `GET /api/v1/entries` - List entries (paginated)
- `GET /api/v1/entries/{id}` - Get single entry
- `POST /api/v1/entries` - Create entry
- `PUT /api/v1/entries/{id}` - Update entry
- `DELETE /api/v1/entries/{id}` - Delete entry

### Search
- `GET /api/v1/search?q=` - Keyword search over entries (tier-ranked)
- `GET /api/v1/search/chunks?q=` - AWMF chunk vector search (dedicated `/leitlinien` page)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://... | PostgreSQL connection |
| `LLAMASERVER_URL` | http://localhost:8080 | Local LLM endpoint (summarize, RAG, embeddings) |
| `OPENROUTER_API_KEY` | (unset) | Cloud fallback for chat/vision OCR — optional |
| `OCR_BACKENDS` | (empty) | Ordered on-demand OCR backends (`tesseract`, `openrouter-vision`); empty = OCR unavailable |
| `MEDWISS_CONTENT_ROOT` | `~/Dokumente/Medizin` | Content root that the source folders resolve against |

## Development

```bash
# Install dependencies
cd ui && bun install

# Run frontend dev server
bun run dev

# Run API dev server
uv run uvicorn api.main:app --reload

# Run linting
ruff check .

# Run tests
uv run --extra test pytest
```

## License

Application code is licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

You may reuse, modify, and share this program. If you distribute a version, or run a modified version over a network, you must release that version's source under the same license. Publishing a closed product from this code is not allowed.

The medical document library is not in this repository and is not covered by this license. This program is not a medical device (not intended for diagnosis, treatment, or monitoring of patients within the meaning of MDR 2017/745 Art. 2) and not medical advice.

## Medical Disclaimer

This software and everything it displays is provided **for educational and
reference purposes only**. It is **not medical advice** and **not a substitute**
for professional judgment, current training, or consultation of the primary
sources (e.g. AWMF/ERC/GRC guidelines in their current versions).

- Clinical content — including scores, calculators, dosages, and emergency
  algorithms — can be outdated, wrong, or incomplete. Verify everything against
  current guidelines before any clinical use.
- In a real medical emergency, call the emergency services
  (**112** Germany / **144** Austria), do not use this application.
- The authors take **no responsibility** and provide **no warranty** of any
  kind for the accuracy, completeness, or timeliness of the content
  (see AGPL-3.0 §15).

See [CONTRIBUTING.md](CONTRIBUTING.md).
