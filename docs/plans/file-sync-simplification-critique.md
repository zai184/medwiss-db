# Critique: Files are the Database — Simplified Live Sync

**Reviewed:** `docs/plans/file-sync-simplification.md` (2026-08-31)
**Reviewer date:** 2026-08-31
**Sources cross-checked:** `api/services/file_sync.py`, `api/services/source_watcher.py`, `api/services/batch_import_worker.py`, `api/services/import_jobs.py`, `api/routers/files.py`, `api/routers/admin.py`, `api/routers/batch_import.py`, `api/routers/references.py`, `api/main.py`, `api/models.py`, `database/models.py`, `database/schema.sql`, `config/__init__.py`, `config/discover_sources.py`, `config/sources.yaml`, `search/faceted.py`, `scripts/run_pipeline.py`, `pipeline/monitor.py`, `ui/src/routes/+page.svelte`, filesystem layout (`~/Projekte/medical/Medwissen/`, `~/Dokumente/Medizin/`)

---

## Summary verdict

The direction is sound and matches what already exists: `FileSyncService` is already the single reconcile core (walks folders, diffs on `source_path` + SHA-256), `SourceWatcher` already provides the live watchdog, and `/admin/sync` + `/admin/sync-status` already exist. Deleting the batch-import job-tracking stack and the per-file throwaway `uuid4()` ImportJob is a genuinely correct cleanup.

But the plan cannot be implemented as written, for two structural reasons. (1) It assumes a unified "`~/Dokumente/Medizin` is the source of truth" while the app actually resolves its source folders to the *workspace-parent* tree (`~/Projekte/medical/Medwissen/`), with two further hardcoded `~/Dokumente/Medizin` outliers (`references.py`, `files.py` AWMF_ROOT) — the proposed Syncthing pair would sync a tree the watcher does not watch. (2) It says "delete `BatchImportWorker`" and "call the pipeline directly" in the same plan, but the single-file pipeline glue (`_process_single_file`) *lives inside* `BatchImportWorker` and is exactly what `FileSyncService` currently calls. There are also three silent-data-loss bugs (Syncthing conflict copies, rename semantics, non-lightweight status poll).

**Revision delta (2026-08-31):** the author revised the plan to unilateral rsync push (daily timer + manual trigger) with `~/Dokumente/Medizin` as the single canonical root (`MEDWISS_CONTENT_ROOT`, retire the `Medwissen` tree). This resolves **B1** and **U1**. Remaining open: **B2**, **U2**, **U3**, **I1–I3**, **M1–M2**, plus a new **M3** (manual-trigger push-vs-pull + daily-vs-live language).

| Severity | Count | Summary |
|----------|-------|---------|
| 🔴 Blocker | 1 | Single-file ingest glue has no relocation target (B1 path model resolved by revision) |
| 🟠 Bug | 2 | Rename destroys entries + manual tags; `/admin/sync-status` is not lightweight (U1 conflict copies resolved) |
| 🟡 Inconsistency | 3 | Wrong deletion path; ImportJob migration surface under-specified; manual-tag vs re-classify precedence undefined |
| 🔵 Missing | 3 | Blocking startup reconcile cost; no reconciliation contract test; trigger-surface decision (M3) |

---

## 1. Blockers

### B1 — Three path conventions; the Syncthing pair would not make the app live

**Resolved in plan revision 2026-08-31:** the plan now names `~/Dokumente/Medizin` as the single canonical root, introduces `MEDWISS_CONTENT_ROOT`, retires the `Medwissen` tree, and targets `/home/medwiss/Dokumente/Medizin` on the VPS so `references.py`'s `Path.home()` keeps working. Remaining detail: the exact `MEDWISS_CONTENT_ROOT` value on the VPS and where `config` reads it (see also M3).

**Problem:** The plan's core premise ("folders under `~/Dokumente/Medizin` are the source of truth", "the app only ever sees one filesystem") does not match how the app actually resolves sources. There are three distinct conventions in the codebase:

1. `FileSyncService._get_all_source_paths` / `SourceWatcher._load_watch_paths` use `load_sources()` → `discover_sources.py` + `config/sources.yaml`, which resolve folders as `workspace_root / "../<folder>"` and *scan the workspace parent*. On this machine the workspace root is `~/Projekte/medical/Medwissen/medwiss-db`, so the watched folders are `~/Projekte/medical/Medwissen/{1_SOPs, 2_Notfall, 3_Leitlinien, …}` — **not** `~/Dokumente/Medizin`.
2. `api/routers/references.py:11` hardcodes `Path.home() / "Dokumente" / "Medizin" / "md" / "medlinks.txt"` = `~/Dokumente/Medizin/md/medlinks.txt`.
3. `api/routers/files.py:41` hardcodes `AWMF_ROOT = "~/Dokumente/Medizin/3_Leitlinien"`.

Both trees exist on disk with the same folder names (`~/Dokumente/Medizin/{1_SOPs,2_Notfall,3_Leitlinien,…}` and `~/Projekte/medical/Medwissen/{1_SOPs,2_Notfall,3_Leitlinien,…}`), and the folder names have already drifted from `sources.yaml` (`2_Leitlinien`/`4_Red Flags`/`6_Pharma` vs actual `2_Notfall`/`4_Red_Flags`/`6_Pharmakologie` — `load_sources` merges by name, so these yaml rows fall through to the phantom-source branch).

The plan proposes syncing local `~/Dokumente/Medizin` ↔ VPS `/srv/medwiss/Dokumente/Medizin`. But the VPS watcher will resolve its sources against the *VPS workspace parent*, not `/srv/medwiss/Dokumente/Medizin`, unless `WORKSPACE_ROOT`/`SOURCES_PATH` are set so that the workspace parent *is* the synced dir. The plan never mentions these env vars, the VPS workspace layout, or `HOME`.

**Impact:** Day-one the synced files land in a directory the watcher and reconcile never scan — the feature is inert. The `medlinks.txt` claim ("once inside the synced tree, edits show immediately") is also wrong as stated: `references.py` reads `Path.home()/Dokumente/Medizin`, so on the VPS it reads `/home/medwiss/Dokumente/Medizin/md/medlinks.txt`, not `/srv/medwiss/Dokumente/Medizin/…`, unless `HOME=/srv/medwiss` or a symlink is arranged.

**Fix:** Pick ONE canonical content root and make all three path sources derive from it (e.g. a `MEDWISS_CONTENT_ROOT` env var read by `config`, `references.py`, and `files.py`). State explicitly: (a) which tree is canonical (`~/Dokumente/Medizin` vs the workspace parent `Medwissen`), (b) the exact VPS layout and the `WORKSPACE_ROOT`/`SOURCES_PATH`/`HOME` values that make the watcher watch the synced dir, and (c) how `references.py`'s `Path.home()` and `files.py`'s `AWMF_ROOT` are unified or kept in sync. Decide whether `sources.yaml`/`discover_sources` are even still needed once the folders are fixed (they currently disagree on folder names).

### B2 — "Delete BatchImportWorker" contradicts "call the pipeline directly"

**Problem:** Work item 3 deletes `api/services/batch_import_worker.py`; work item 2 says `FileSyncService` should "call the pipeline directly" and "remove the per-file `uuid4()` temp ImportJob". But the single-file pipeline glue *is* `BatchImportWorker._process_single_file` (`api/services/batch_import_worker.py:351-436`), which `FileSyncService.sync_new_file`/`sync_modified_file` currently call (`file_sync.py:293-296`, `343-347`). It wires together duplicate check, `BatchProcessor.process_file`, `_resolve_classifications_for_result`, hash computation, `_create_entry_from_result`, and `_generate_and_store_embedding` — plus helpers `_handle_duplicate`, `_resolve_classifications_for_result`, `_create_entry_from_result`, `_generate_and_store_embedding` (`batch_import_worker.py:99-330`).

Deleting `batch_import_worker.py` removes the very function `FileSyncService` depends on, and the plan names no destination for that ~130 lines of glue.

**Impact:** There is no "pipeline" to call directly once the worker is gone — the plan's two central moves are mutually inconsistent and block implementation.

**Fix:** Specify that the single-file ingest logic is promoted out of `BatchImportWorker` into `FileSyncService` (or a new `api/services/single_file_ingest.py`), enumerating the moved methods (`_process_single_file` → e.g. `ingest_file`, `_resolve_classifications_for_result`, `_create_entry_from_result`, `_generate_and_store_embedding`, and the duplicate/hash check collapsed to "hash unchanged → skip"). Then `batch_import_worker.py` (job orchestration only) becomes deletable. Note `FileSyncService` must keep `BatchProcessor` (`pipeline/batch_processor.py`) and `DuplicateDetector` (`pipeline/duplicate_detector.py`) as dependencies.

---

## 2. Bugs

### U1 — Syncthing conflict/version files will be imported as new entries (silent duplicates)

**Resolved in plan revision 2026-08-31:** Syncthing is dropped in favour of unilateral rsync push, which produces no `.sync-conflict`/`.stversions` artifacts. The `.obsidian/` exclusion is explicit; no exclusion code change is needed beyond that.

**Problem:** The plan asserts "conflict copies land in `.stversions`/`.sync-conflict` — checked during reconcile, never auto-merged." No such check exists and no work item adds one. `FileSyncService.scan_source_folders` does `path.rglob("*")` filtered only by suffix (`file_sync.py:183-197`); `SourceFolderEventHandler._is_supported_file` filters only by suffix (`source_watcher.py:87`). There is no `.sync-conflict`/`.stversions`/dot-directory exclusion anywhere in `api/`, `pipeline/`, or `config/` (verified by grep). `discover_subcategories` skips dotfolders, but `scan_source_folders` does not.

**Impact:** Every Syncthing conflict copy (`report.sync-conflict-20260831-…pdf`) and every `.stversions` historical version gets imported as a NEW entry with a fresh ID — exact duplicates of real entries. This directly contradicts the plan's "local wins / never auto-merged" policy and pollutes the DB silently.

**Fix:** In `scan_source_folders` and the watcher, skip any path whose basename contains `.sync-conflict` and any path under a `.stversions`/`.stfolder` directory (skip dot-directories during `rglob` generally). Add it as an explicit work item, and add a regression test (see M2).

### U2 — Rename destroys the entry and its manual tags

**Problem:** Principle 1 states "Rename → re-tagged", and work item 5 states "reconcile never overwrites manual tags". But there is no rename handling anywhere. `SourceFolderEventHandler` implements only `on_created`/`on_modified`/`on_deleted` — `on_moved` is not overridden, so a rename *within* a watched folder fires the base-class no-op (no live update at all). `FileSyncService.detect_changes` (`file_sync.py:205-268`) matches only by `source_path`: a rename shows up as old-path-in-DB-but-not-in-FS → `deleted_entries`, and new-path-in-FS-not-in-DB → `new_files`. The next reconcile therefore **hard-deletes the old entry and creates a fresh one**.

**Impact:** On every rename, the entry ID changes and all manual tags, `zusammenfassung`, and any other user-edited columns are lost; the plan's "reconcile never overwrites manual tags" is false for the rename case it explicitly names.

**Fix:** Add rename support — implement `on_moved` in the watcher and/or detect delete+create pairs with matching `file_hash` in `detect_changes` — and map a rename to `sync_modified_file` on the *existing* entry (preserving ID + manual columns), re-deriving only folder-derived tags. State explicitly that "re-tagged" means re-derive path-derived tags, not recreate.

### U3 — `/admin/sync-status` is not lightweight; 10 s polling would re-hash the whole tree

**Problem:** The plan says the UI "polls `GET /admin/sync-status` (lightweight: counts + last-change timestamp) every 10 s". The actual endpoint (`api/routers/files.py:299-357`) calls `sync_service.scan_source_folders()` (full recursive SHA-256 of every file) **and** `sync_service.detect_changes()` (full DB query + hash comparison) plus a per-source `rglob` file count on every request, and returns `last_sync=None` and `sync_errors=[]` hardcoded. The "last-change timestamp" the UI is supposed to key on does not exist.

**Impact:** Polling every 10 s means hashing thousands of PDFs (incl. `3_Leitlinien`) every 10 s — pathological I/O on the single-worker VPS, and the change-detection signal the plan relies on is absent. The "live" goal is unachievable as specced.

**Fix:** Make `/admin/sync-status` cheap: keep an in-memory `last_change_at` + pending-count updated by the watcher, persist `last_sync` on `run_sync`, and return those without re-hashing. Reserve the full hash scan for `POST /admin/sync`. (Note the real paths are `/api/v1/files/admin/sync-status` and `/api/v1/files/admin/sync` — the plan's `/admin/sync*` shorthand drops the `/files` prefix.)

---

## 3. Inconsistencies

### I1 — Deletion list names a nonexistent file and conflates the engine with the orchestrator

**Problem:** Work item 3 lists `api/services/batch_processor.py` as a file to delete. It does not exist — the actual path is `pipeline/batch_processor.py`, and it must **stay**: `FileSyncService` imports `calculate_file_hash` from it (`file_sync.py:30`), and it is `BatchProcessor` — the extraction engine the plan wants to call "directly". The file whose deletion removes "batch import" is `api/services/batch_import_worker.py`.

**Fix:** Correct the list: delete `api/services/batch_import_worker.py`, `api/services/import_jobs.py`, `api/routers/batch_import.py`, `scripts/batch_import_cli.py`, `pipeline/monitor.py`; keep `pipeline/batch_processor.py` and `pipeline/duplicate_detector.py` (and state this explicitly so reviewers don't "clean up" them).

### I2 — ImportJob deletion migration surface is under-specified

**Problem:** The plan says "ImportJob model + table (migration)" but the deletion is broader than a table drop. `KnowledgeEntry.import_batch_id` has `ForeignKey("import_jobs.id", ondelete="SET NULL")` and a `relationship("ImportJob")` (`database/models.py:278-321`); `schema.sql` has the table + 2 indexes (`schema.sql:151-164`); `_create_entry_from_result` assigns `import_batch_id=self.job_id` (`batch_import_worker.py:287`); `api/models.py` defines `ImportJobStatus/Create/Update/Response` (`:402-442`); `api/services/__init__.py` re-exports the worker + service (`__init__.py:3-6`); and the generated `ui/src/lib/api-types.d.ts` carries the `/batch-import` paths.

**Fix:** Enumerate the full deletion surface: migration drops the FK on `knowledge_entries.import_batch_id` → drops the column → drops `import_jobs` + indexes; remove the model/relationship, the Pydantic models, `ImportJobService`, the `__init__.py` exports, `api/routers/batch_import.py`, `scripts/batch_import_cli.py`, and regenerate `ui/src/lib/api-types.d.ts` via `./scripts/gen-api.sh`. Also remove the `import_batch_id=` assignment from the relocated ingest logic (B2).

### I3 — "Re-run regex classify on change" vs "never overwrite manual tags" is unresolved

**Problem:** Work item 5 says folder-derived Fachgebiet + regex classification "run during watcher upserts" *and* "reconcile never overwrites manual tags". There is no mechanism distinguishing a manually-edited tag from an auto-derived one. On a modified file the current UPDATE branch already re-runs `apply_hierarchy_labels` (`batch_import_worker.py:410-415`), and the plan's "changed → re-extract/re-tag" would re-resolve classifications — clobbering a manual Fachgebiet/Diagnose/Symptom edit unless the reconcile explicitly skips user-modified dimensions.

**Fix:** Define precedence concretely: either add a per-entry (or per-dimension) "tags manually edited" flag set on UI tag edits, or state that reconcile assigns tags only on CREATE and never on UPDATE (which matches the current UPDATE branch that leaves fachgebiete/diagnosen/symptome untouched), re-deriving only hierarchy labels/unterkategorie.

---

## 4. Missing / omissions

### M1 — Startup reconcile is synchronous and re-hashes the whole tree on every restart

**Problem:** "Run `FileSyncService.run_sync(dry_run=False)` before serving" is blocking and full-cost: `run_sync` hashes every file, and `sync_new_file`/`sync_modified_file` commit per file (`file_sync.py:305,353`). With a single uvicorn worker, the API is down for the duration (minutes on a large tree), and every restart re-pays the full hash cost even when nothing changed.

**Fix:** Run startup reconcile in a background thread (non-blocking) and surface progress via the existing `/admin/sync-status`; optionally persist a watermark (last full-scan time / max mtime) so unchanged trees skip the hash pass.

### M2 — No reconciliation contract test or conflict-file exclusion test

**Problem:** "Files are the database" is exactly the kind of behavior that silently drifts. The plan's verification is manual only.

**Fix:** Add a small contract test with a temp source dir: create → entry appears; modify → entry updates (hash changes, tags preserved); delete → entry removed; and a `.sync-conflict-*.pdf` / `.stversions` fixture asserting it is *not* imported. Not a v1 gate, but cheap and directly guards U1/U2.

### M3 — Manual-trigger push vs pull, and daily cadence vs "live within seconds"

**Problem:** The plan's manual trigger is a local `systemctl start medwiss-sync` (push), while the existing UI "Synchronisieren" button only triggers the *reconcile* (`POST /admin/sync`), not the transfer. The plan defers a web button that transfers files to "a separate decision" (VPS pull via a read-only ssh key). This is left unresolved. Separately, with a daily timer the goal text ("appears in the UI after the next sync + reconcile") now conflicts with principle 3 / work item 4 ("live", "every 10 s"): the 10 s poll reflects VPS-local file changes, not local→VPS propagation, which is at most daily (or manual).

**Fix:** Decide the trigger surface explicitly: (a) local push only — recommended, since local holds the ssh key and the VPS never reaches into `~/Dokumente/Medizin`, matching the stated trust boundary; or (b) VPS pull via a read-only forced-command ssh key, so a web button can transfer. Restate the "live" claims as "watcher reacts to files as they land after a sync", not "seconds after a local edit".

---

## 5. What the plan gets right

| Decision | Assessment |
|----------|------------|
| Filesystem-as-source-of-truth + one reconcile core | ✅ Matches existing `FileSyncService` (already diffs on `source_path` + SHA-256, `detect_changes`/`run_sync`). |
| Keep `SourceWatcher` for liveness | ✅ Already implemented and wired in `api/main.py` lifespan (`:22-42`). |
| Remove per-file `uuid4()` throwaway ImportJob in the sync path | ✅ Real anti-pattern (`file_sync.py:292,343` create a temp job just to call `_process_single_file`). |
| Delete batch-import job-tracking stack | ✅ Correct cleanup; `refresh_search_index` is now a no-op (`search/faceted.py:351`), so dropping that call site is safe. |
| No SSE/WebSocket for single-user app | ✅ Sound; polling is the right call if the poll is cheap (see U3). |
| `medlinks.txt` live-parse, no app change | ✅ `references.py` parses per request (`parse_medlinks` → `get_references`), so no caching work needed — but only once the path model (B1) is fixed. |
| Unilateral rsync over Syncthing | ✅ Correct for a one-way, read-only-source topology; avoids conflict/version artifacts entirely. |

---

## 6. Codebase facts verified

| Claim in plan | Verified against | Result |
|---------------|------------------|--------|
| `FileSyncService` walks folders and diffs on `source_path` + SHA-256 | `api/services/file_sync.py:167-268` | ✅ |
| `SourceWatcher` = one Observer per source folder, 0.5 s settle wait | `api/services/source_watcher.py:301-329,158,188` | ✅ |
| `on_created/modified → upsert`, `on_deleted → delete` already exist | `source_watcher.py:137-239` | ✅ |
| Per-file `uuid4()` temp ImportJob in sync path | `file_sync.py:292-293,343-344` | ✅ |
| `GET /admin/sync-status` + `POST /admin/sync` exist | `api/routers/files.py:299,360` (under `/files` prefix) | ✅ |
| Startup reconcile already runs on API start | `api/main.py:22-42` (only starts watcher; no reconcile) | ❌ (new work, correctly identified) |
| `medlinks.txt` parsed live per request | `api/routers/references.py:11,133-139` | ✅ |
| `api/services/batch_processor.py` exists to delete | glob: only `pipeline/batch_processor.py` exists | ❌ wrong path |
| Single-file pipeline glue lives in `BatchImportWorker._process_single_file` | `api/services/batch_import_worker.py:351-436` | ✅ (contradicts deletion) |
| `ImportJob` table + FK on `knowledge_entries.import_batch_id` | `database/models.py:236,278-280`; `schema.sql:151-164` | ✅ (migration scope bigger than stated) |
| `refresh_search_index` must survive the deletion | `search/faceted.py:351` (no-op) | ✅ safe to drop |
| Conflict-copy/`.stversions` exclusion exists | grep `sync-conflict\|stversions\|ignore_patterns` in api/pipeline/config | ❌ absent |
| Rename handling exists (`on_moved`) | `source_watcher.py` (only created/modified/deleted) | ❌ absent |
| `AWMF_ROOT` / `references.py` hardcode `~/Dokumente/Medizin` | `files.py:41`; `references.py:11` | ✅ (third path convention) |

---

## 7. Recommended plan revisions (priority order)

1. **B2** — Specify where `_process_single_file` (and its helpers) move when `BatchImportWorker` is deleted; enumerate the moved methods.
2. **M3** — Decide the manual-trigger surface (local push vs VPS pull); reconcile the "live within seconds" language with the daily cadence.
3. **U2** — Add rename detection (`on_moved` or delete+create-with-same-hash) mapped to update, preserving ID + manual tags.
4. **U3** — Make `/admin/sync-status` cheap (in-memory change timestamp/counts, no re-hash); only `POST /admin/sync` runs the full pass.
5. **I1/I2** — Correct the deletion list; enumerate the full ImportJob removal surface (FK, column, models, service, exports, generated types).
6. **I3** — Define manual-tag vs re-classify precedence.
7. **M1/M2** — Background/non-blocking startup reconcile; add a reconciliation contract test.

---

## 8. Conclusion

**Revise before implement.** The architecture is sound, and two of the original blockers (B1 path model, U1 conflict copies) are now resolved by the unilateral-rsync decision. Remaining before day one: **B2** (single-file glue relocation) and **M3** (trigger surface + cadence language). **U2**/**U3** are silent-data-loss/perf bugs to fold into the work items.
