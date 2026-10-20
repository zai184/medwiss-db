# Plan: Files are the Database — Simplified Live Sync

**Status:** Draft, awaiting approval
**Date:** 2026-08-31
**Goal:** `~/Dokumente/Medizin` is the single source of truth — authoritative and **read-only** to the app. It is copied unilaterally (one-way) to the VPS; the DB is a derived index (tags, summaries, chunks). Changes appear in the UI after the next sync + reconcile.

## Principles

1. **Filesystem is the database.** Delete a file → entry disappears. Rename → re-tagged. No import jobs, no queues, no duplicate strategies beyond "hash unchanged → skip".
2. **One reconcile core.** `FileSyncService` (`api/services/file_sync.py`) is the only code that walks folders and diffs against the DB (`source_path` + SHA-256).
3. **Live everywhere.** Watcher on the running API keeps the index current; UI reflects changes without reload.
4. **Unilateral file sync.** `~/Dokumente/Medizin` is copied one-way to the VPS (rsync push). Nothing is ever synced back, and neither the app nor the sync ever writes to the source tree.

## Architecture

```
tux@local (authoritative, read-only to app)    medwiss@VPS
~/Dokumente/Medizin  ──rsync push──>  $MEDWISS_DEPLOY_HOST:/srv/medwiss/corpus
   (you edit)      daily timer + manual trigger         │
                                                         ▼
                                        SourceWatcher (in API process)
                                          on_created/modified → extract → classify → upsert
                                          on_deleted → remove entry
                                        + startup reconcile (heals drift)
                                        + POST /admin/sync (manual reconcile)
                                                         │
                                                         ▼
                                        PostgreSQL (derived index: tags, summary, chunks)
                                                         │
                                                         ▼
                                        SvelteKit UI ← polling /admin/sync-status
```

## Work items

### 1. Local → VPS file sync: unilateral rsync push
- **One-way by construction.** rsync runs only from local with `~/Dokumente/Medizin` as source; there is no reverse command anywhere. The source tree is only *read* — never altered or deleted by the app or the sync. The VPS copy is a disposable mirror.
- **Transport: adopt the existing hardened script** on the host (path in `.private/infra.md`) — already one-way (`~/Dokumente/Medizin/` → `$MEDWISS_DEPLOY_HOST:/srv/medwiss/corpus/`, SSH port from `.private/deploy.env`), dry-run by default, dest-only `--delete`, lands files medwiss-owned via `--rsync-path="sudo -u medwiss rsync"`, excludes `KI/`, `Fortbildungen/`, `*.bkp`/`*.nbib`/`*.enw`, and logs to `scripts/logs/`. Do **not** invent a parallel rsync command.
- **Target on VPS is `/srv/medwiss/corpus`**, with the existing symlink `/srv/medwiss/Dokumente/Medizin → corpus` making `api/routers/references.py`'s `Path.home()/Dokumente/Medizin` work (medwiss user home = `/srv/medwiss`). Never create `/home/medwiss`.
- **Cadence + manual trigger:** local systemd pair `medwiss-sync.service` (oneshot: the script with `--apply --delete`) + `medwiss-sync.timer` (daily). Manual trigger = `systemctl start medwiss-sync`. The push runs on local because local holds the key and "the VPS cannot pull from tux" is already a hard rule in the deploy playbook. The VPS UI "Synchronisieren" button keeps triggering only the reconcile (`POST /admin/sync`).
- **No Syncthing.** Bidirectional sync, conflict copies (`.sync-conflict-*`) and versioning (`.stversions`) are exactly the artifacts that would pollute the index; one-way rsync has none of them and no daemon/device-ID state.

#### Canonical content root — retire the duplicate tree
- **The duplicate tree is already gone** (the stub folders under the old workspace-parent `Medwissen/` tree were removed 2026-08-31; only the repo + `.env` remain). Consequence: the app's current source resolution (`config/sources.yaml` + `config/discover_sources.py`, relative to the workspace parent) now finds **zero** local sources — the root switch below is a hard prerequisite, not a cleanup.
- Introduce `MEDWISS_CONTENT_ROOT` (local: `~/Dokumente/Medizin`, VPS: `/srv/medwiss/corpus`) and make `config`, `api/routers/references.py`, and `api/routers/files.py` (`AWMF_ROOT`) all derive from it, so `load_sources()`/`discover_sources()` resolve against the canonical tree on both sides.

### 2. Keep + slim the live watcher (SourceWatcher)
- Keep `SourceWatcher` (watchdog, one Observer per source folder) — this is what makes "change file → UI updates" live.
- Slim handlers:
  - `on_created`/`on_modified` → upsert via `FileSyncService.sync_new_file`/`sync_modified_file` (extract → regex classify → optional LLM tags → save). Keep the 0.5 s settle wait.
  - `on_deleted` → delete entry by `source_path`.
  - **Remove the per-file `uuid4()` temp ImportJob** — call the pipeline directly.
- Add **startup reconcile**: on API start, run `FileSyncService.run_sync(dry_run=False)` before serving (heals anything missed while the API or Syncthing was down).

### 3. Delete the batch-import stack
- `api/services/batch_import_worker.py`, `api/services/batch_processor.py`
- `api/services/import_jobs.py`, `ImportJob` model + table (migration)
- `api/routers/batch_import.py` (routes `POST/GET /batch-import...`)
- `scripts/batch_import_cli.py`
- `pipeline/monitor.py` (legacy second watchdog) — fold `scripts/run_pipeline.py` onto `pipeline/orchestrator.py`.
- `FileSyncService.sync_new_file` stops creating temp jobs; duplicate strategy collapses to "hash unchanged → skip, changed → re-extract".

### 4. Live UI updates
- SvelteKit polls `GET /admin/sync-status` (lightweight: counts + last-change timestamp) every 10 s while relevant pages are open (dashboard, search, entry lists); on change → refetch list. No SSE/WebSocket for a single-user app.
- Entry detail pages refetch on focus.
- Admin page: "Synchronisieren" button stays (manual full pass); batch-import UI section removed.

### 5. Tagging (the actual remaining feature)
- No change to the 5 tag dimensions (Fachgebiete, Diagnosen, Symptome, Dokumenttypen, Ordner-Labels).
- Folder-derived Fachgebiet and regex classification (`regex_classifier.py` + `data/classification_library.txt`) run during watcher upserts; LLM classification optional (works without Llamaserver).
- Tag edits in UI remain the source for those columns; reconcile never overwrites manual tags, only creates entries for new/changed files.

## Non-goals
- Parallel/parallelized import, progress bars with per-file job API (log lines suffice).
- WebSockets/SSE.
- Merging conflicts automatically.

## Risks / notes
- Single uvicorn worker on VPS — watcher runs in-process; restarting the API restarts the watcher (startup reconcile covers the gap).
- rsync writes to the VPS mirror as the ssh user; file modes may differ from local — reconcile reads only, no chmod assumptions. `--delete` affects only the VPS mirror (source is never touched).
- First full rsync of the Medizin tree is a one-time bulk (3_Leitlinien PDFs); run it once before enabling the watcher, and use `--dry-run` the first time.

## Verification
1. Edit a file locally → `systemctl start medwiss-sync` (manual trigger) → file lands on VPS → watcher upserts → UI shows updated title/tags without reload.
2. Delete a file locally → next daily sync (or manual trigger) → mirror deletes it → entry gone.
3. Kill API + edit files → restart API → startup reconcile applies the backlog.
4. `medlinks.txt` edit → References page updated immediately (live parse, same synced path).
5. `ruff check`, `bun run check`, existing tests; grep confirms no references to deleted modules.
