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
│   ├── search/+page.svelte      # Search interface
│   ├── eingabe/+page.svelte     # Entry form
│   ├── bibliothek/+page.svelte  # Library with folder categories
│   └── settings/+page.svelte    # User settings
├── lib/
│   ├── api.ts          # Axios API client
│   ├── stores/         # Svelte stores
│   │   ├── search.ts   # Search state management
│   │   └── entryForm.ts # Form state
│   └── components/
│       ├── SearchResults.svelte
│       ├── FileUpload.svelte
│       ├── KIPreview.svelte
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
| API calls | `lib/api.ts` | Axios instance with auth header; types from `lib/api-types.d.ts` (generated) |
| Shared state | `lib/stores/` | Svelte 5 runes or stores |
| Reusable UI | `lib/components/` | Svelte components |
| Charts | `lib/components/charts/` | Chart.js wrappers |
| Styling | `app.css` | Tailwind directives + custom |

## CONVENTIONS

- Svelte 5 runes (`$state`, `$derived`, `$effect`) for local state
- Stores for cross-component state (search, form)
- Components use TypeScript (`<script lang="ts">`)
- Props typed with interfaces
- API base URL from `VITE_API_URL` env var
- Tailwind CSS for styling

## ANTI-PATTERNS

- **NEVER** call API directly from components - use `lib/api.ts`
- **NEVER** edit `lib/api-types.d.ts` by hand — `./scripts/gen-api.sh` after Pydantic / route changes
- **NEVER** mutate store values directly - use store methods
- **ALWAYS** handle loading/error states for async operations
- **NEVER** use inline styles - use Tailwind classes
