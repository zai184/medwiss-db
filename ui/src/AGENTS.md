# UI MODULE

**Parent:** [../AGENTS.md](../AGENTS.md) | **App:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW
SvelteKit frontend for the Medical Knowledge Database.

## STRUCTURE

```
src/
├── routes/              # SvelteKit file-based routing
│   ├── +page.svelte    # Dashboard (root)
│   ├── +layout.svelte  # Root layout with nav
│   ├── search/+page.svelte      # Search (keyword + facet filters)
│   ├── eingabe/+page.svelte     # Entry form with KI upload
│   ├── entry/[id]/              # Entry detail (+ edit/)
│   ├── bibliothek/+page.svelte  # Library with folder categories
│   ├── leitlinien/+page.svelte  # AWMF chunk search / RAG
│   ├── notfall/+page.svelte     # Emergency algorithms & SOPs
│   ├── rechner/+page.svelte     # Clinical calculator links
│   ├── referenz/+page.svelte    # Reference links (medlinks.txt)
│   ├── pubmed/+page.svelte      # PubMed search
│   ├── icd11/+page.svelte       # ICD-11 browser
│   └── admin/+page.svelte       # Labels, classification, sync
├── lib/
│   ├── api.ts          # Axios API client (no auth)
│   ├── stores/         # Svelte stores
│   │   ├── search.ts   # Search state management
│   │   ├── entryForm.ts # Form state
│   │   └── entryViewer.ts # Gallery overlay state
│   └── components/
│       ├── SearchResults.svelte
│       ├── FacetFilters.svelte
│       ├── FileUpload.svelte
│       ├── FileViewer.svelte
│       ├── KIPreview.svelte
│       ├── TranscribeModal.svelte
│       ├── MultiSelect.svelte
│       ├── StatCard.svelte
│       ├── ActivityList.svelte
│       └── charts/     # Chart.js components
│           ├── FachDistribution.svelte
│           └── DiagnoseBarChart.svelte
└── app.css             # Tailwind + custom styles
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add page | `routes/` | SvelteKit file-based routing |
| API calls | `lib/api.ts` | Axios instance; types from `lib/api-types.d.ts` (generated) |
| Shared state | `lib/stores/` | Svelte 5 runes or stores |
| Reusable UI | `lib/components/` | Svelte components |
| Charts | `lib/components/charts/` | Chart.js wrappers |
| Styling | `app.css` | Tailwind directives + custom |

## CONVENTIONS

- Svelte 5 runes (`$state`, `$derived`, `$effect`) for local state
- Stores for cross-component state (search, form)
- Components use TypeScript (`<script lang="ts">`)
- Props typed with interfaces
- API base URL from `VITE_API_URL` env var (dev: Vite proxies `/api`)
- Tailwind CSS for styling

## ANTI-PATTERNS

- **NEVER** call API directly from components - use `lib/api.ts`
- **NEVER** edit `lib/api-types.d.ts` by hand — `./scripts/gen-api.sh` after Pydantic / route changes
- **NEVER** mutate store values directly - use store methods
- **ALWAYS** handle loading/error states for async operations
- **NEVER** use inline styles - use Tailwind classes
