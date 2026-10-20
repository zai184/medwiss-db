<script lang="ts">
  import { onMount } from 'svelte';
  import { ExternalLink, Search, Loader2, Calculator, Star } from 'lucide-svelte';
  import { classificationsApi, type DiagnoseResponse } from '$lib/api';
  import {
    CALCULATORS,
    DISCIPLINES,
    DISCIPLINE_COLORS,
    calculatorMatches,
    type CalculatorLink,
    type DisciplineDef,
  } from '$lib/calculators';

  // Tier 1: provider search links for any term.
  // Tier 2: curated deep links in ui/src/lib/calculators.ts (MDCalc favorites).
  const providers = [
    { name: 'MDCalc', url: (q: string) => `https://www.mdcalc.com/search?q=${encodeURIComponent(q)}` },
    { name: 'QxMD Calculate', url: (q: string) => `https://qxmd.com/calculate?s=${encodeURIComponent(q)}` },
  ];

  let diagnoses = $state<DiagnoseResponse[]>([]);
  let query = $state('');
  let loading = $state(true);
  let error = $state<string | null>(null);

  const trimmed = $derived(query.trim());
  const searching = $derived(trimmed.length >= 2);
  const matches = $derived(
    searching
      ? diagnoses
          .filter((d) => d.name.toLowerCase().includes(trimmed.toLowerCase()))
          .slice(0, 60)
      : []
  );
  const curatedMatches = $derived(searching ? CALCULATORS.filter((c) => calculatorMatches(c, trimmed)) : []);

  function matchDiagnosesFor(calc: CalculatorLink): string[] {
    return diagnoses
      .filter((d) => calculatorMatches(calc, d.name))
      .map((d) => d.name)
      .slice(0, 5);
  }

  /** Calculators of one discipline, ordered by subgroup definition. */
  function disciplineCalcs(d: DisciplineDef): CalculatorLink[] {
    const items = CALCULATORS.filter((c) => c.discipline === d.name);
    if (!d.groups) return items;
    const ungrouped = items.filter((c) => !c.group);
    const grouped = d.groups.map((g) => ({ g, items: items.filter((c) => c.group === g) }));
    return [...ungrouped, ...grouped.flatMap((x) => x.items)];
  }

  onMount(async () => {
    try {
      diagnoses = await classificationsApi.getDiagnosen();
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : 'Fehler beim Laden der Diagnosen';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>Rechner | MedWiss DB</title>
</svelte:head>

<div class="rechner-page">
  <header class="page-header">
    <h1>Klinische Rechner</h1>
  </header>

  <section class="content-section search-box">
    <div class="search-input-row">
      <span class="search-icon"><Search size={18} /></span>
      <input
        type="text"
        bind:value={query}
        aria-label="Suchbegriff für Rechner"
      />
    </div>

    {#if searching}
      <div class="provider-links">
        {#each providers as p (p.name)}
          <a href={p.url(trimmed)} target="_blank" rel="noopener noreferrer" class="provider-link">
            <Calculator size={16} />
            <span>{p.name}: „{trimmed}“</span>
            <ExternalLink size={14} />
          </a>
        {/each}
      </div>
    {/if}
  </section>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if searching && curatedMatches.length > 0}
    <section class="content-section">
      <h2 class="section-title"><span class="title-icon"><Star size={16} /></span> Passende Favoriten ({curatedMatches.length})</h2>
      <div class="chip-grid">
        {#each curatedMatches as c (c.url)}
          <a
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            class="match-button"
            style={`border-left-color: ${DISCIPLINE_COLORS[c.discipline] ?? 'var(--color-primary)'}`}
            title={[c.discipline, c.group, ...matchDiagnosesFor(c)].filter(Boolean).join(' · ')}
          >
            <span class="chip-label">{c.name}</span>
            <span class="chip-provider">{[c.discipline, c.group].filter(Boolean).join(' · ')}</span>
            <ExternalLink size={12} />
          </a>
        {/each}
      </div>
    </section>
  {/if}

  {#if !searching}
    {#each DISCIPLINES as d (d.name)}
      {@const items = disciplineCalcs(d)}
      {#if items.length > 0}
        <section class="content-section discipline-box">
          <h2 class="section-title" style={`border-left-color: ${d.color}`}>{d.name}</h2>
          {#if d.groups}
            {#each d.groups as g (g)}
              {@const groupItems = items.filter((c) => c.group === g)}
              {#if groupItems.length > 0}
                <h3 class="cat-title">{g}</h3>
                <div class="chip-grid group-grid">
                  {#each groupItems as c (c.url)}
                    <a href={c.url} target="_blank" rel="noopener noreferrer" class="curated-chip" title={c.name}>
                      <span class="chip-label">{c.name}</span>
                      <ExternalLink size={12} />
                    </a>
                  {/each}
                </div>
              {/if}
            {/each}
            {@const ungrouped = items.filter((c) => !c.group)}
            {#if ungrouped.length > 0}
              <div class="chip-grid group-grid">
                {#each ungrouped as c (c.url)}
                  <a href={c.url} target="_blank" rel="noopener noreferrer" class="curated-chip" title={c.name}>
                    <span class="chip-label">{c.name}</span>
                    <ExternalLink size={12} />
                  </a>
                {/each}
              </div>
            {/if}
          {:else}
            <div class="chip-grid">
              {#each items as c (c.url)}
                <a href={c.url} target="_blank" rel="noopener noreferrer" class="curated-chip" title={c.name}>
                  <span class="chip-label">{c.name}</span>
                  <ExternalLink size={12} />
                </a>
              {/each}
            </div>
          {/if}
        </section>
      {/if}
    {/each}
  {/if}

  {#if loading}
    <div class="loading">
      <span class="spin"><Loader2 size={24} /></span>
      <span>Lade Diagnosen…</span>
    </div>
  {:else if matches.length > 0}
    <section class="content-section">
      <h2 class="section-title">Passende Diagnosen ({matches.length}{matches.length === 60 ? '+' : ''})</h2>
      <div class="chip-grid">
        {#each matches as d (d.id)}
          {#each providers as p (p.name)}
            <a
              href={p.url(d.name)}
              target="_blank"
              rel="noopener noreferrer"
              class="diagnose-chip"
              title={`${d.name} bei ${p.name} suchen`}
            >
              <span class="chip-label">{d.name}</span>
              <span class="chip-provider">{p.name}</span>
              <ExternalLink size={12} />
            </a>
          {/each}
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .rechner-page {
    padding: var(--space-6) var(--space-8);
    max-width: 1400px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: var(--space-6);
  }

  .page-header h1 {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin: 0;
  }

  .content-section {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    margin-bottom: var(--space-6);
  }

  .discipline-box .section-title {
    border-left: 3px solid var(--color-primary);
    padding-left: var(--space-3);
  }

  .search-input-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 0 var(--space-4);
    background: var(--color-background-secondary);
  }

  .search-input-row input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    padding: var(--space-4) 0;
    font-size: var(--font-size-lg);
    color: var(--color-text-primary);
  }

  .provider-links {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    margin-top: var(--space-4);
  }

  .provider-link {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-background-secondary);
    color: var(--color-text-primary);
    text-decoration: none;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .provider-link:hover {
    border-color: var(--color-primary);
    background: var(--color-background-tertiary);
  }

  .section-title {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin: 0 0 var(--space-4);
  }

  .title-icon {
    vertical-align: -2px;
    margin-right: var(--space-2);
    color: var(--color-warning, #f59e0b);
  }

  .cat-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: var(--space-4) 0 var(--space-2);
  }

  .cat-title:first-of-type {
    margin-top: 0;
  }

  .group-grid {
    margin-bottom: var(--space-2);
  }

  .chip-grid {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .curated-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-left: 3px solid var(--color-primary);
    border-radius: var(--radius-lg);
    background: var(--color-background-secondary);
    color: var(--color-text-primary);
    text-decoration: none;
    font-size: var(--font-size-sm);
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .curated-chip:hover {
    background: var(--color-background-tertiary);
  }

  .match-button {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--color-border);
    border-left: 3px solid var(--color-primary);
    border-radius: var(--radius-lg);
    background: var(--color-background-secondary);
    color: var(--color-text-primary);
    text-decoration: none;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .match-button:hover {
    background: var(--color-background-tertiary);
  }

  .diagnose-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-background-secondary);
    color: var(--color-text-primary);
    text-decoration: none;
    font-size: var(--font-size-sm);
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .diagnose-chip:hover {
    border-color: var(--color-primary);
    background: var(--color-background-tertiary);
  }

  .chip-provider {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
  }

  .error-banner {
    padding: var(--space-4);
    border: 1px solid var(--color-danger, #dc2626);
    border-radius: var(--radius-lg);
    color: var(--color-danger, #dc2626);
    margin-bottom: var(--space-6);
  }

  .loading {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    color: var(--color-text-tertiary);
    padding: var(--space-8) 0;
    justify-content: center;
  }

  .spin {
    display: inline-flex;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 768px) {
    .rechner-page {
      padding: var(--space-4);
    }
  }
</style>
