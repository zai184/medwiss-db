<script lang="ts">
  import { onMount } from 'svelte';
  import { Search, ExternalLink, Loader2, BookOpen, SlidersHorizontal } from 'lucide-svelte';
  import { pubmedApi, type PubmedResult } from '$lib/api';

  let query = $state('');
  let results = $state<PubmedResult[]>([]);
  let total = $state(0);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let searched = $state(false);
  let builtQuery = $state('');
  let expanded = $state<Set<string>>(new Set());
  let page = $state(0);

  const PAGE_SIZE = 20;
  const MAX_RESULTS = 100;

  // Filters
  let titleFilter = $state('');
  let authorFilter = $state('');
  let ptypeFilter = $state('');
  let publisherFilter = $state('');
  let datePreset = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');
  let sort = $state('relevance');
  let showFilters = $state(false);

  const sortOptions: { value: string; label: string }[] = [
    { value: 'relevance', label: 'Relevanz' },
    { value: 'pub_date', label: 'Neueste zuerst' },
    { value: 'Author', label: 'Autor (A-Z)' },
    { value: 'JournalName', label: 'Zeitschrift (A-Z)' },
  ];

  const ptypes: { value: string; label: string }[] = [
    { value: 'case_reports', label: 'Case Reports' },
    { value: 'clinical_study', label: 'Clinical Study' },
    { value: 'clinical_trial', label: 'Clinical Trial' },
    { value: 'dataset', label: 'Dataset' },
    { value: 'review', label: 'Review' },
  ];

  const datePresets: { value: string; label: string }[] = [
    { value: '1y', label: '1 Jahr' },
    { value: '5y', label: '5 Jahre' },
    { value: '10y', label: '10 Jahre' },
    { value: 'custom', label: 'Benutzerdefiniert' },
  ];

  async function doSearch() {
    if (!query.trim() && !titleFilter.trim() && !authorFilter.trim() && !ptypeFilter && !publisherFilter.trim()) return;
    await goToPage(0);
  }

  function buildFilters() {
    return {
      q: query.trim() || undefined,
      title: titleFilter.trim() || undefined,
      author: authorFilter.trim() || undefined,
      ptype: ptypeFilter || undefined,
      publisher: publisherFilter.trim() || undefined,
      date_preset: datePreset || undefined,
      date_from: datePreset === 'custom' && dateFrom ? dateFrom.replaceAll('-', '/') : undefined,
      date_to: datePreset === 'custom' && dateTo ? dateTo.replaceAll('-', '/') : undefined,
      sort,
    };
  }

  async function goToPage(pageNum: number) {
    if (pageNum < 0 || pageNum * PAGE_SIZE >= MAX_RESULTS) return;
    loading = true;
    error = null;
    try {
      const resp = await pubmedApi.search(buildFilters(), PAGE_SIZE, pageNum * PAGE_SIZE);
      results = resp.results;
      total = resp.total;
      builtQuery = resp.query;
      page = pageNum;
      searched = true;
      expanded = new Set();
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : 'Suche fehlgeschlagen';
      results = [];
    } finally {
      loading = false;
    }
  }

  // Cap the browsable window at the top 100 hits; keep the real `total` for display.
  const shownTotal = $derived(Math.min(total, MAX_RESULTS));
  const totalPages = $derived(Math.max(1, Math.ceil(shownTotal / PAGE_SIZE)));
  const hasNext = $derived((page + 1) * PAGE_SIZE < shownTotal);

  function toggleAbstract(pmid: string) {
    const next = new Set(expanded);
    if (next.has(pmid)) next.delete(pmid);
    else next.add(pmid);
    expanded = next;
  }

  // PubMed structured abstracts arrive as one plain string with section
  // labels ("Background: ... Methods: ..."). Split into { label, text }
  // blocks rendered as their own sections; text is auto-escaped by Svelte.
  const ABSTRACT_LABELS =
    'Background|Objective|Objectives|Purpose of review|Purpose|Key messages|Aim|Introduction|Importance|Context|Methods|Method|Design|Setting|Participants|Subjects|Interventions|Intervention|Main outcome measures|Outcome measures|Results|Findings|Conclusions|Conclusion|Limitations|Discussion|Trial registration|Copyright|Language|Hintergrund|Zielsetzung|Patienten und Methodik|Patienten und Methoden|Fragestellung|Ziele|Ziel|Methodik|Methoden|Ergebnisse|Ergebnis|Schlussfolgerungen|Schlussfolgerung|Fallberichte|Fallbericht|Diskussion';
  const ABSTRACT_SECTION_RE = new RegExp(
    `(^|[\\n\\s])(${ABSTRACT_LABELS})\\s*[.:]`,
    'gi'
  );

  function abstractSections(text: string): { label: string | null; text: string }[] {
    const sections: { label: string | null; text: string }[] = [];
    let cursor = 0;
    let label: string | null = null;
    let m: RegExpExecArray | null;
    ABSTRACT_SECTION_RE.lastIndex = 0;
    while ((m = ABSTRACT_SECTION_RE.exec(text)) !== null) {
      const chunk = text.slice(cursor, m.index).trim();
      if (chunk) sections.push({ label, text: chunk });
      label = m[2];
      cursor = m.index + m[0].length;
    }
    const rest = text.slice(cursor).trim();
    if (rest) sections.push({ label, text: rest });
    return sections;
  }

  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (q) {
      query = q;
      doSearch();
    }
  });
</script>

<svelte:head>
  <title>PubMed | MedWiss DB</title>
</svelte:head>

<div class="pubmed-page">
  <header class="page-header">
    <div class="header-icon">
      <BookOpen size={28} />
    </div>
    <div class="header-content">
      <h1>PubMed Suche</h1>
      <p class="subtitle">Live-Literatursuche über die NCBI E-utilities API</p>
    </div>
  </header>

  <form class="search-bar" onsubmit={(e) => { e.preventDefault(); doSearch(); }}>
    <span class="search-icon"><Search size={20} /></span>
    <input
      type="text"
      bind:value={query}
      aria-label="PubMed Suchbegriff"
    />
    <button
      type="submit"
      class="search-btn"
      disabled={loading || (!query.trim() && !titleFilter.trim() && !authorFilter.trim() && !ptypeFilter && !publisherFilter.trim())}
    >
      {#if loading}
        <Loader2 size={18} class="spin" />
      {:else}
        <Search size={18} />
      {/if}
      <span>Suchen</span>
    </button>
  </form>

  <button class="filters-toggle" onclick={() => (showFilters = !showFilters)}>
    <SlidersHorizontal size={16} />
    <span>Filter</span>
  </button>

  {#if showFilters}
    <div class="filters-panel">
      <div class="filter-row">
        <label class="filter-field">
          <span class="filter-label">Titel</span>
          <input type="text" bind:value={titleFilter} aria-label="Titel-Filter" />
        </label>
        <label class="filter-field">
          <span class="filter-label">Autor</span>
          <input type="text" bind:value={authorFilter} aria-label="Autor-Filter" />
        </label>
        <label class="filter-field">
          <span class="filter-label">Artikeltyp</span>
          <select bind:value={ptypeFilter} aria-label="Artikeltyp-Filter">
            <option value="">Alle</option>
            {#each ptypes as pt (pt.value)}
              <option value={pt.value}>{pt.label}</option>
            {/each}
          </select>
        </label>
        <label class="filter-field">
          <span class="filter-label">Zeitschrift</span>
          <input type="text" bind:value={publisherFilter} aria-label="Zeitschriften-Filter" />
        </label>
      </div>
      <div class="filter-row">
        <label class="filter-field">
          <span class="filter-label">Erscheinungsdatum</span>
          <select bind:value={datePreset} aria-label="Datums-Filter">
            <option value="">Beliebig</option>
            {#each datePresets as dp (dp.value)}
              <option value={dp.value}>{dp.label}</option>
            {/each}
          </select>
        </label>
        {#if datePreset === 'custom'}
          <label class="filter-field">
            <span class="filter-label">Von</span>
            <input type="date" bind:value={dateFrom} aria-label="Startdatum" />
          </label>
          <label class="filter-field">
            <span class="filter-label">Bis</span>
            <input type="date" bind:value={dateTo} aria-label="Enddatum" />
          </label>
        {/if}
        <label class="filter-field">
          <span class="filter-label">Sortierung</span>
          <select bind:value={sort} aria-label="Sortierungs-Filter">
            {#each sortOptions as so (so.value)}
              <option value={so.value}>{so.label}</option>
            {/each}
          </select>
        </label>
      </div>
    </div>
  {/if}

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">
      <Loader2 size={24} class="spin" />
      <span>Suche bei PubMed...</span>
    </div>
  {:else if searched}
    {#if results.length === 0}
      <div class="empty">Keine Ergebnisse für "{query}"</div>
    {:else}
      <div class="result-meta">
        <span>{total} Ergebnisse{#if total > MAX_RESULTS} — zeige 1–100{/if}</span>
        <span>Artikel nach Relevanz sortiert</span>
      </div>
      {#if builtQuery}
        <div class="built-query" title={builtQuery}>{builtQuery}</div>
      {/if}
      <ul class="result-list">
        {#each results as r (r.pmid)}
          <li class="result-card">
            <div class="result-top">
              <h2 class="result-title">
                <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
              </h2>
              {#if r.abstract}
                <button
                  class="abstract-toggle"
                  onclick={() => toggleAbstract(r.pmid)}
                  aria-expanded={expanded.has(r.pmid)}
                >
                  {expanded.has(r.pmid) ? 'Abstract ausblenden' : 'Abstract anzeigen'}
                </button>
              {/if}
            </div>
            <div class="result-meta-line">
              {#if r.authors.length > 0}
                <span class="authors">{r.authors.join(', ')}</span>
              {/if}
              {#if r.journal}
                <span class="journal">{r.journal}</span>
              {/if}
              {#if r.date}
                <span class="date">{r.date}</span>
              {/if}
              {#if r.doi}
                <span class="doi">doi: {r.doi}</span>
              {/if}
              <span class="pmid">PMID: {r.pmid}</span>
              <a href={r.url} target="_blank" rel="noopener noreferrer" class="pubmed-link">
                <ExternalLink size={14} />
                PubMed
              </a>
            </div>
            {#if expanded.has(r.pmid) && r.abstract}
              <div class="abstract">
                {#each abstractSections(r.abstract) as section (section.label)}
                  <div class="abs-section">
                    {#if section.label}
                      <div class="abs-label">{section.label}</div>
                    {/if}
                    <p>{section.text}</p>
                  </div>
                {/each}
              </div>
            {/if}
          </li>
        {/each}
      </ul>

      <nav class="pagination" aria-label="Ergebnis-Navigation">
        <button class="page-btn" disabled={page === 0} onclick={() => goToPage(page - 1)}>
          ← Zurück
        </button>
        <span class="page-info">Seite {page + 1} / {totalPages}</span>
        <button class="page-btn" disabled={!hasNext} onclick={() => goToPage(page + 1)}>
          Weiter →
        </button>
      </nav>
    {/if}
  {/if}
</div>

<style>
  .pubmed-page {
    padding: var(--space-6) var(--space-8);
    max-width: 960px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    gap: var(--space-4);
    margin-bottom: var(--space-8);
  }

  .header-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 52px;
    height: 52px;
    border-radius: var(--radius-lg);
    background: var(--color-primary-subtle);
    color: var(--color-primary);
    flex-shrink: 0;
  }

  .page-header h1 {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin: 0;
  }

  .subtitle {
    font-size: var(--font-size-base);
    color: var(--color-text-tertiary);
    margin: var(--space-1) 0 0;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-2) var(--space-3);
    margin-bottom: var(--space-6);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .search-bar:focus-within {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-focus);
  }

  .filters-toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    margin-bottom: var(--space-4);
    transition: all var(--transition-fast);
  }

  .filters-toggle:hover {
    background: var(--color-background-tertiary);
    color: var(--color-primary);
    border-color: var(--color-primary);
  }

  .filters-panel {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .filter-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
  }

  .filter-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    flex: 1;
    min-width: 140px;
  }

  .filter-label {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .filter-field input,
  .filter-field select {
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    color: var(--color-text-primary);
    background: var(--color-background-secondary);
    transition: border-color var(--transition-fast);
  }

  .filter-field input:focus,
  .filter-field select:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .built-query {
    font-family: monospace;
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    background: var(--color-background-secondary);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    margin-bottom: var(--space-4);
    overflow-x: auto;
    white-space: nowrap;
  }

  .search-icon {
    color: var(--color-text-tertiary);
    flex-shrink: 0;
  }

  .search-bar input {
    flex: 1;
    border: none;
    outline: none;
    font-size: var(--font-size-base);
    color: var(--color-text-primary);
    background: transparent;
    padding: var(--space-2) 0;
  }

  .search-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: none;
    border-radius: var(--radius-md);
    background: var(--color-primary);
    color: white;
    font-weight: var(--font-weight-medium);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: background var(--transition-fast);
    flex-shrink: 0;
  }

  .search-btn:hover:not(:disabled) {
    background: var(--color-primary-dark);
  }

  .search-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error-banner {
    padding: var(--space-3) var(--space-4);
    background: var(--color-error-subtle);
    color: var(--color-error);
    border-radius: var(--radius-lg);
    font-size: var(--font-size-sm);
    margin-bottom: var(--space-6);
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    padding: var(--space-12);
    color: var(--color-text-tertiary);
  }

  .empty {
    text-align: center;
    padding: var(--space-12);
    color: var(--color-text-tertiary);
    background: var(--color-background-primary);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-xl);
  }

  .result-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    color: var(--color-text-tertiary);
    margin-bottom: var(--space-4);
  }

  .result-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-4);
    margin-top: var(--space-6);
  }

  .page-btn {
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-background-primary);
    color: var(--color-primary);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    transition: background var(--transition-fast);
  }

  .page-btn:hover:not(:disabled) {
    background: var(--color-primary-subtle);
  }

  .page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-info {
    font-size: var(--font-size-sm);
    color: var(--color-text-tertiary);
  }

  .result-card {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-5);
    transition: box-shadow var(--transition-fast);
  }

  .result-card:hover {
    box-shadow: var(--shadow-md);
  }

  .result-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--space-3);
  }

  .result-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    margin: 0;
    flex: 1;
  }

  .result-title a {
    color: var(--color-primary);
    text-decoration: none;
    transition: color var(--transition-fast);
  }

  .result-title a:hover {
    color: var(--color-primary-dark);
    text-decoration: underline;
  }

  .abstract-toggle {
    flex-shrink: 0;
    font-size: var(--font-size-xs);
    color: var(--color-primary);
    background: var(--color-primary-subtle);
    border: none;
    border-radius: var(--radius-sm);
    padding: var(--space-1) var(--space-3);
    cursor: pointer;
    white-space: nowrap;
    transition: background var(--transition-fast);
  }

  .abstract-toggle:hover {
    background: var(--color-primary-light);
  }

  .result-meta-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
    margin-top: var(--space-2);
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
  }

  .authors {
    color: var(--color-text-secondary);
  }

  .journal {
    font-style: italic;
  }

  .doi, .pmid {
    font-family: monospace;
  }

  .pubmed-link {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    color: var(--color-primary);
    text-decoration: none;
    font-weight: var(--font-weight-medium);
  }

  .pubmed-link:hover {
    text-decoration: underline;
  }

  .abstract {
    margin-top: var(--space-4);
    padding: var(--space-4);
    background: var(--color-background-secondary);
    border-left: 3px solid var(--color-primary);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    line-height: 1.6;
    color: var(--color-text-secondary);
  }

  .abs-section {
    margin-bottom: var(--space-3);
  }

  .abs-section:last-child {
    margin-bottom: 0;
  }

  .abs-label {
    font-weight: var(--font-weight-semibold);
    font-variant: small-caps;
    color: var(--color-text-primary);
    margin-bottom: var(--space-1);
  }

  .abs-section p {
    margin: 0;
  }

  :global(.spin) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @media (max-width: 768px) {
    .pubmed-page {
      padding: var(--space-4);
    }

    .page-header h1 {
      font-size: var(--font-size-2xl);
    }

    .result-top {
      flex-direction: column;
    }
  }
</style>
