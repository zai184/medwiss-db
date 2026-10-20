<script lang="ts">
  import { onMount } from 'svelte';
  import { ExternalLink, RefreshCw, Loader2 } from 'lucide-svelte';
  import {
    referencesApi,
    type ReferenceSection,
  } from '$lib/api';

  let sections = $state<ReferenceSection[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function load() {
    loading = true;
    error = null;
    try {
      sections = await referencesApi.getReferences();
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : 'Fehler beim Laden';
    } finally {
      loading = false;
    }
  }

  onMount(load);
</script>

<svelte:head>
  <title>Referenz | MedWiss DB</title>
</svelte:head>

<div class="referenz-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Medizinische Referenzen</h1>
    </div>
    <button class="refresh-btn" onclick={load} disabled={loading} title="Neu laden">
      {#if loading}
        <Loader2 size={18} class="spin" />
      {:else}
        <RefreshCw size={18} />
      {/if}
    </button>
  </header>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading && sections.length === 0}
    <div class="loading">
      <Loader2 size={24} class="spin" />
      <span>Laden...</span>
    </div>
  {:else}
    <div class="sections-grid">
      {#each sections as section (section.title)}
        <section class="ref-section">
          <h2 class="section-title">{section.title}</h2>
          {#each section.sub as sub (sub.title ?? '_root')}
            <div class="ref-subsection">
              {#if sub.title}
                <h3 class="subsection-title">{sub.title}</h3>
              {/if}
              <ul class="link-list">
                {#each sub.links as link, i (link.url + '#' + i)}
                  <li>
                    <a href={link.url} target="_blank" rel="noopener noreferrer" class="ref-link">
                      <span class="link-label">{link.label}</span>
                      <span class="link-domain">{link.url}</span>
                      <ExternalLink size={14} class="link-icon" />
                    </a>
                  </li>
                {/each}
              </ul>
            </div>
          {/each}
        </section>
      {/each}
    </div>
  {/if}
</div>

<style>
  .referenz-page {
    padding: var(--space-6) var(--space-8);
    max-width: 1400px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
    margin-bottom: var(--space-8);
  }

  .page-header h1 {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin: 0;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    background: var(--color-background-primary);
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }

  .refresh-btn:hover:not(:disabled) {
    background: var(--color-background-tertiary);
    color: var(--color-primary);
    border-color: var(--color-primary);
  }

  .refresh-btn:disabled {
    opacity: 0.5;
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

  .sections-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: var(--space-6);
  }

  .ref-section {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    padding: var(--space-5);
    transition: box-shadow var(--transition-fast);
  }

  .ref-section:hover {
    box-shadow: var(--shadow-md);
  }

  .section-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-bold);
    color: var(--color-primary);
    margin: 0 0 var(--space-4);
    padding-bottom: var(--space-3);
    border-bottom: 2px solid var(--color-primary-subtle);
  }

  .ref-subsection + .ref-subsection {
    margin-top: var(--space-5);
    padding-top: var(--space-4);
    border-top: 1px solid var(--color-border);
  }

  .subsection-title {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 var(--space-2);
  }

  .link-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .ref-link {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
    text-decoration: none;
    color: var(--color-text-primary);
    transition: background var(--transition-fast);
    min-width: 0;
  }

  .ref-link:hover {
    background: var(--color-background-tertiary);
  }

  .link-label {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    min-width: 0;
    flex-shrink: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .link-domain {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 0;
  }

  :global(.link-icon) {
    color: var(--color-text-tertiary);
    flex-shrink: 0;
    opacity: 0;
    transition: opacity var(--transition-fast);
  }

  .ref-link:hover :global(.link-icon) {
    opacity: 1;
  }

  :global(.spin) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @media (max-width: 768px) {
    .referenz-page {
      padding: var(--space-4);
    }

    .page-header h1 {
      font-size: var(--font-size-2xl);
    }

    .sections-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
