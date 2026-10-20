# Bidirectional Corpus Sync (tux ↔ VPS)

**Status:** Proposal — needs boss decision (option A vs C) before implementation.
**Date:** 2026-09-03

## Problem

Files are edited on **tux** and on the **VPS**. The VPS is always on, tux is not.
Today's model is one-way (tux → VPS rsync), so VPS-side edits get clobbered and
tux never sees them. We need bidirectional sync **without clobbering** and
without the corpus getting into a half-merged state.

## Shared invariants (whatever we pick)

1. **Files remain the database.** Both hosts ingest independently; each host's
   DB mirrors its local corpus. Tags are assigned on create only — untouched.
2. **Conflicts become files, never merges.** A conflicted file must land in the
   corpus as its own entry (conflict copy) so the watcher ingests it and a
   human picks. Git-style inline conflict markers are FORBIDDEN — they would be
   ingested as content.
3. **Corpus becomes writable to the app** (both hosts) for the "edit md files"
   feature: API writes via tmp-file + rename inside `MEDWISS_CONTENT_ROOT`
   (`.md`/`.txt` only, size cap), then updates `file_hash` so the watcher's
   reconcile sees an unchanged hash (no re-extract loop).
4. **Never sync the DBs.** Only files cross hosts.

## Option A — Syncthing on the corpus folder (recommended)

- Daemon on both hosts; VPS is the always-on hub, tux catches up whenever it
  is on. Exactly the "VPS always on / tux not always on" shape.
- Conflicts: Syncthing writes `name.sync-conflict-<date>.ext` next to the
  original — invariant 2 for free. The watcher ingests the copy as a new
  entry; human merges and deletes the loser.
- `.stfolder` marker lives in `~/Dokumente/Medizin` (tux) and
  `/srv/medwiss/corpus` (VPS); ignore patterns for `.tmp`, `~` temp files so
  rsync/watcher temp names don't race.
- Replaces: `medwiss-sync.timer` + `sync-medwiss-corpus.sh` (retire both).
- Cost: one daemon per host, one-time pairing. Note: the old "no Syncthing"
  rule predates the bidirectional requirement — needs explicit revoke.

## Option C — Unison, timer-driven (boring-minimal)

- Same folder pair, one `unison -batch` profile run by a timer on tux (and a
  rarer one on the VPS for its own edits).
- Conflicts: `-batch` skips them and logs — a wrapper turns each skipped file
  into a conflict copy + notification (small script we own).
- Cost: sync only advances when a run happens; VPS-side edits wait for tux
  (acceptable: VPS edits land on tux at next run). No daemon.

## Rejected

- **Git transport:** conflict markers in prose + merge UX; content conflicts
  would be ingested. Fails invariant 2.
- **DB-as-edit-surface** (no file write-back): contradicts the requirement
  that files are edited on both hosts.

## Implementation sketch (Option A)

1. Revoke the no-Syncthing rule (this doc = the ADR).
2. VPS: install syncthing (host module), share `/srv/medwiss/corpus`,
   listen on the WireGuard overlay only (address in `.private/infra.md`, port 22000 + GUI on loopback).
3. tux: share `~/Dokumente/Medizin`, device id = VPS.
4. App write path: `POST /api/v1/entries/{id}/file` (md/txt write-through,
   hash stamp); service user gets corpus write access on both hosts
   (`ReadWritePaths` on the VPS unit).
5. Watcher: confirm `on_moved`/temp-name handling is Syncthing-safe (it
   already handles rsync temp renames — verify `.syncthing.*` tmp suffix).
6. Smoke: edit on tux → appears on VPS corpus + ingested; edit on VPS via API
   → appears on tux; simultaneous edit → conflict copy ingested on both.
