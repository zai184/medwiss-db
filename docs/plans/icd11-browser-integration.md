# ICD-11 Embedded Browser — Integration Plan

**Goal:** Add a new `/icd11` page with the official WHO Embedded Classification Tools (ECT)
browser, letting users browse the full ICD-11 tree in German, search by term/code, and
optionally pick a code to copy back into the app.

**Date:** 2026-08-26  
**Status:** Draft

---

## Why ECT (not iframe or external link)

| Approach | Verdict |
|----------|---------|
| `icd.who.int/ct/icd11_mms/de/release` in an iframe | WHO SPA — no code-selection callback, control is fully external, looks like a foreign site |
| Link to WHO site | No integration at all; user leaves the app |
| **WHO ECT library** (`@whoicd/icd11ect` npm) | Official, German, fully embedded; version/feature matches our API client; the sanctioned integration path |

---

## What ECT provides

The `@whoicd/icd11ect@1.8.0` package is a UMD bundle (React under the hood) exporting:

```ts
ECT.configure({
  apiServerUrl: string;   // e.g. "https://id.who.int/icdapi"
  apiSecured: boolean;     // true = needs token, but WHO public API allows free browsing
  source: string;          // "mms" = Mortalitats- und Morbiditatsstatistiken
  language: string;        // "de"
  minorVersion: string;    // "2026-01" — matches our icd11.py client
});

ECT.EmbedcedBrowser(containerId, {
  iNo: string;   // unique instance id (e.g. "mb-main")
});
```

The browser:
- Full ICD-11 chapter tree with search box (term or code)
- German UI, set by `language`
- When a user clicks a category, fires a callback (`handleSelectEntity`) with the
  URI and title — we can hook this to offer "copy code" / "use as diagnosis"
- Licensed under WHO ICD-11 license (already agreed for the API client in .env)

---

## Page architecture

### `/ui/src/routes/icd11/+page.svelte`

**Layout:**
- Full-width page (same `admin-container` style max-width, or full bleed)
- Page header: title "ICD-11 Browser", subtitle "Klassifikation der Weltgesundheitsorganisation"
- A `<div id="icd11-browser">` container — ECT mounts its React tree into this
- A small copy bar below/above the browser: when a code is selected via
  `handleSelectEntity`, show the URI + title + a "Kopieren" button

**ECT loading (client-only):**
- ECT is UMD (depends on `window`), so it cannot be imported in SSR
- Use Svelte `onMount()` to dynamically load ECT
- CSS from CDN: `https://icdcdn.who.int/embeddedct/icd11ect-1.8.css`
- JS from CDN: `https://icdcdn.who.int/embeddedct/icd11ect-1.8.js`
- Or install via bun: `bun add @whoicd/icd11ect` in `/ui` and import in `onMount`

**CDN vs npm decision:** CDN is simpler for now (no build config for UMD in Vite).
The CSS must load before the JS. Inject both in `onMount` and call `ECT.configure`
then `ECT.EmbeddedBrowser('icd11-browser', {iNo: 'mb-main'})`.

**Code selection callback:**
ECT's `handleSelectEntity` is fired internally. To get a hook, use ECT's
`browserSelectionChanged` event or poll `ECT.getBrowserSelection(iNo)`.
The ECT config accepts an `onLoadedUriChange` callback — pass this in the
config object to get notified when the user navigates.

```ts
ECT.configure({
  apiServerUrl: "https://id.who.int/icdapi",
  apiSecured: true,    // we have tokens; or false for public browse-only
  source: "mms",
  language: "de",
  minorVersion: "2026-01",
  // callback on entity selection:
  onLoadedUriChange: (uri, title) => {
    selectedCode = { uri, title };
  },
});
```

### Sidebar

Add to `ui/src/routes/+layout.svelte` after the existing nav:

```
├── <a href="/icd11" class="nav-item"> …
│     <BookOpen size={18} />
│     <span>ICD-11</span>
```

Import `BookOpen` from `lucide-svelte` (already a dependency).

---

## Auth token exchange

The ECT needs an ICD-API OAuth2 token when `apiSecured: true`. Two options:

### Option A — Backend proxy endpoint (recommended)
Add `GET /api/v1/icd11/token` that:
1. Uses the existing `ICD11Client` (which already handles token caching in
   `api/services/icd11.py`)
2. Returns `{token, expires_at}` — the frontend passes this to ECT as
   `requestHeaders: {Authorization: "Bearer <token>"}`

This keeps the client secret server-side and lets us reuse the existing
`ICD11Client.token` property (which auto-refreshes).

### Option B — ECT with `apiSecured: false`
The WHO ICD-API has a free tier that allows basic browsing without a token.
If token-less browsing works for the tree+search, skip the proxy endpoint.
Test this first — if browsing works without auth, Option B is simpler.

**Recommendation:** Test Option B first. If tree navigation fails without token,
add the proxy endpoint (Option A). The `ICD11Client` already caches the token.

---

## Implementation steps

| Step | File(s) | What |
|------|---------|------|
| 1 | `ui/src/routes/icd11/+page.svelte` | Create page: header + `<div id="icd11-browser">` + script |
| 2 | `ui/src/routes/icd11/+page.svelte` | `onMount`: load ECT CSS/JS from CDN, call `configure` + `EmbeddedBrowser` |
| 3 | `ui/src/routes/+layout.svelte` | Add ICD-11 nav item to sidebar (after Admin link, before the gap) |
| 4 | (optional) `api/routers/icd11.py` | Token proxy endpoint if Option B fails |
| 5 | `bun run check` | Verify 0 errors |
| 6 | Browser test | Navigate to /icd11, verify ECT tree loads, search works, code selection callback fires |

### Files touched
- `ui/src/routes/icd11/+page.svelte` (new)
- `ui/src/routes/+layout.svelte` (1 line: add nav link)
- (optional) `api/routers/icd11.py` + `api/main.py` (register router)

---

## Edge cases & risks

| Risk | Mitigation |
|------|-----------|
| ECT JS fails to load (CDN down, ad blocker) | Show a fallback "ICD-11 Browser konnte nicht geladen werden" + link to WHO site |
| `apiSecured: true` without valid token = 401 | Test Option B (unsecured) first; add proxy only if needed |
| ECT version drift | Pin to CDN path `icd11ect-1.8.js`; upgrade only when WHO releases new version |
| SvelteKit SSR tries to import ECT | Never `import ECT` at module level; only in `onMount` |
| Large bundle (750KB) | CDN chunk loads lazily after main app; no impact on initial load |

---

## Open question

Should the code-selection bar offer "Füge zur Diagnose hinzu" (insert code into
the current entry's diagnose label)? Or is "Kopieren" enough for v1?

---

**Next:** On approval, execute steps 1–6 in order.
