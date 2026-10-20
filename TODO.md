## TODO

### OCR decision — remote via OpenRouter, NOT the bigmodel (Z.ai) provider

Remote OCR uses **OpenRouter `z-ai/glm-4.6v`** with the existing
`OPENROUTER_API_KEY` — no second provider. The dedicated **GLM-OCR** model
(`glm-ocr`, layout_parsing) lives on the **bigmodel provider** = Zhipu's
platform (`api.z.ai` international / `open.bigmodel.cn` China), which needs a
separate `ZAI_API_KEY` / `ZHIPU_API_KEY` + resource package; it is **not** on
OpenRouter. Rejected 2026-09-07 (prototype `glmocr-maas` backend built then
removed). If table/formula-quality OCR is ever needed later, upgrade path is
local phase-2 (`glmocr-selfhost` on tux GPU or PaddleOCR), not the Z.ai cloud.

### Open decision — bidirectional corpus sync (tux ↔ VPS)

Boss must pick **A (Syncthing)** or **C (Unison)** before implementation.
Full proposal: `docs/plans/bidirectional-corpus-sync.md`.
- Context: files are edited on tux AND on the VPS; VPS is always on, tux is
  not always on. Today only tux → VPS rsync (one-way); reverse edits clobber.
- A: Syncthing — live, conflict copies ingested as new entries.
- C: Unison — timer-based, simpler, conflicts logged.
- Recommendation: A. Status: awaiting boss pick (added 2026-09-03).

## Open-Source Release (started 2026-10-15)

Repo is AGPL-3.0, no CLA, corpus excluded, gitleaks clean. Remaining before public push:

1. **Personal infrastructure** — done in the working tree 2026-10-15.
   Deploy host/port live in gitignored `.private/deploy.env`. Notes live in
   `.private/infra.md`. `.sisyphus/` and `docs/audits/` are removed from the
   tree and gitignored. Old git history on `backup` still has the strings;
   the first public push must be a fresh snapshot.
2. **`ui/bun.lock` advisories** (~5 min): `cd ui && bun update`, then
   `bun run check && bun test` (Info 3 second half — build-time/unreachable,
   routine bump).
3. **Boss check `.envrc`**: confirm it only points at `.env`/paths, no real
   keys; else `git rm --cached .envrc` + `.gitignore`. (Agent must not open it.)
4. **Optional: kill last svelte-check warning** (~1 h): restructure edit-page
   form into a keyed child component, or approve one `svelte-ignore`
   `state_referenced_locally` (deliberate initial snapshot, reset effect exists).
5. **Boss: UI smoke** — KI-preview icon spin/colors + bibliothek row icon colors
   now actually apply (were silently dead scoped CSS); entry→entry navigation
   (detail + edit) shows the new entry without reload.
6. **Publish**: new public remote, push, keep `backup` remote local-only.

Done 2026-10-15: stored-XSS High fixed (`highlight.ts` + tests), audit findings
cleared (deps, requirements.txt deleted, 127.0.0.1 bind, is_relative_to,
defusedxml), README warning block, svelte-check 32→1 warnings.
