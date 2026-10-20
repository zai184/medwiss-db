# Classify-From-Filename + ICD-11 Validation

> **Status:** Planned | **Date:** 2026-08-26

## Goal

Classify entries' diagnoses and symptoms by feeding filenames to the LLM in bulk, building a keyword-to-diagnosis mapping, then applying it locally. Enrich results with ICD-11 codes via the WHO ICD API.

## Problem

- 2,865 entries in the database have empty `diagnosen` and `symptome` fields
- Batch import was run without LLM classification for these fields
- Running full OCR + LLM classification on all entries is too expensive
- But folder paths and filenames contain enough information to extract diagnoses

## Architecture

```
POST /api/v1/admin/classify-from-filename
         |
         v
+---------------------+
| 1. Fetch entries     |  All entries missing diagnoses
|    with empty diag   |  (or all with --force)
+---------------------+
         |
         v
+---------------------+
| 2. Batch filenames   |  ~200 per batch, ~15 batches
|    to Llamaserver    |  LLM extracts: disease name + ICD-10 code
+---------------------+
         |
         v
+---------------------+
| 3. ICD-11 validate   |  For each extracted diagnosis:
|    via WHO API       |  - Look up ICD-11 code
|    (parallel)        |  - Store alongside ICD-10
+---------------------+
         |
         v
+---------------------+
| 4. Merge mappings    |  Deduplicate across batches
|    into one dict     |  -> keyword -> {name, icd10, icd11}
+---------------------+
         |
         v
+---------------------+
| 5. Local matching    |  Regex keyword match on filename + path
|    (instant)         |  Link matched diagnoses via M2M
+---------------------+
         |
         v
+---------------------+
| 6. Return stats      |  { classified, skipped, new_diagnoses }
+---------------------+
```

## Components

| File | Action | Purpose |
|---|---|---|
| `.env` | Modify | Add `ICD11_CLIENT_ID`, `ICD11_CLIENT_SECRET` |
| `api/config.py` | Modify | Add pydantic fields for ICD-11 creds |
| `api/services/icd11.py` | Create | ICD-11 API client: OAuth token + search |
| `api/services/filename_classifier.py` | Create | Core: batching, LLM calls, mapping, matching |
| `api/routers/admin.py` | Create | `POST /api/v1/admin/classify-from-filename` |
| `api/main.py` | Modify | Register admin router |
| `ui/src/routes/admin/+page.svelte` | Modify | Trigger button + results display |
| Database migration | Create | Add `icd11_code` column to `diagnosen` table |

## ICD-11 Client (`api/services/icd11.py`)

```python
class ICD11Client:
    """OAuth2 client for WHO ICD-11 API."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_expires: float = 0

    async def _ensure_token(self) -> str:
        """Get/refresh OAuth2 token from WHO endpoint."""

    async def search(self, query: str, language: str = "de") -> list[ICD11Result]:
        """Search ICD-11 by term. Returns [{code, title, uri}]."""
```

**Flow:**
1. POST to `https://icdaccessmanagement.who.int/connect/token` with client credentials
2. GET `https://id.who.int/icd/release/11/mms/search?q={term}` with Bearer token
3. Cache token for ~55 min (expires in 60)

## Filename Classifier (`api/services/filename_classifier.py`)

```python
class FilenameClassifier:
    def __init__(self, db: Session, icd11: ICD11Client | None = None):
        self.db = db
        self.icd11 = icd11  # optional — degrades gracefully without it

    async def classify_all(self, *, force: bool = False, dry_run: bool = False) -> ClassifyResult:
        """Main entry point."""

    def _build_llm_prompt(self, entries: list[FilenameEntry]) -> str:
        """Batch of ~200 entries -> LLM prompt."""

    async def _parse_llm_response(self, response: str) -> dict[str, DiagnosisInfo]:
        """Parse LLM JSON -> keyword dict."""

    async def _validate_with_icd11(self, diagnoses: dict[str, DiagnosisInfo]) -> dict[str, DiagnosisInfo]:
        """Enrich each diagnosis with ICD-11 code via WHO API."""

    def _match_entry(self, filename: str, folder: str, keyword_dict: dict) -> list[DiagnosisInfo]:
        """Regex match one entry -> matched diagnoses."""

    def _link_diagnoses(self, entry: KnowledgeEntry, diagnoses: list[DiagnosisInfo]) -> None:
        """Create/lookup Diagnosis rows + M2M link."""
```

## Database Schema Change

Add column to `diagnosen` table:

```sql
ALTER TABLE diagnosen ADD COLUMN icd11_code VARCHAR(20);
```

ICD-10 `code` stays as primary. ICD-11 is supplementary.

## LLM Prompt

```
Du bist ein medizinischer Klassifizierer. Extrahiere Diagnosen aus Dateinamen.

Analysiere die folgenden Dateinamen und Ordner-Pfade.
Gib für jede relevante Diagnose den deutschen Namen und den ICD-10-Code an.

Dateinamen:
1. [Ordner: 5_Faecher/Kardiologie] 2026 VHF Therapie im Wandel.pdf
2. [Ordner: 3_Leitlinien] 015-076p3_S2k_Frueher-Schwangerschaftsverlust.pdf
3. [Ordner: Fortbildung 2026] Screenshot_20260323-190657.png

Regeln:
- Nur spezifische Diagnosen, keine allgemeinen Begriffe
- Bei nutzlosen Dateinamen (Screenshot, Datum) -> ueberspringen
- ICD-10-Code nur wenn sicher, sonst null
- Deutsche Namen

Antworte NUR mit JSON:
{
  "keywords": {
    "VHF": {"name": "Vorhofflimmern", "code": "I48"},
    "Schwangerschaftsverlust": {"name": "Spontanabort", "code": "O03"}
  }
}
```

## ICD-11 Enrichment (after LLM)

```python
async def _validate_with_icd11(self, diagnoses):
    for keyword, diag in diagnoses.items():
        if not diag.code:  # no ICD-10 code -> skip ICD-11
            continue
        results = await self.icd11.search(diag.name)
        if results:
            diag.icd11_code = results[0].code  # best match
    return diagnoses
```

## API Endpoint

```
POST /api/v1/admin/classify-from-filename
Content-Type: application/json

{
  "force": false,      // re-classify entries that already have diagnoses
  "dry_run": true      // return mapping without writing
}
```

### Response

```json
{
  "total_entries": 2865,
  "classified": 1847,
  "skipped": 1018,
  "new_diagnoses_created": 42,
  "icd11_enriched": 38,
  "mapping_size": 89,
  "dry_run": false
}
```

## Frontend (Admin Page)

New section "Dateinamen-Klassifizierung":
- Toggle: "Nur unklassifizierte" (default) / "Alle neu klassifizieren"
- Toggle: "Dry Run" (default: on)
- Button: "Klassifizieren"
- Results panel: classified count, skipped, new diagnoses, ICD-11 enriched

## Estimated LOC

| File | Lines |
|---|---|
| `api/services/icd11.py` | ~60 |
| `api/services/filename_classifier.py` | ~140 |
| `api/routers/admin.py` | ~45 |
| `api/main.py` change | ~3 |
| `api/config.py` change | ~2 |
| `admin/+page.svelte` change | ~50 |
| DB migration | ~10 |

**Total: ~310 lines**

## Execution Order

1. Add ICD-11 config + `.env` entries
2. Write `icd11.py` client
3. Write `filename_classifier.py` core logic
4. Write `admin.py` router
5. Register in `main.py`
6. Add DB migration for `icd11_code` column
7. Update admin page UI
8. Test end-to-end
