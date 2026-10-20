<script lang="ts">
  import { onMount } from 'svelte';
  import { BookOpen, Copy, Check, ExternalLink } from 'lucide-svelte';

  let browserLoaded = $state(false);
  let loadError = $state(false);
  let selectedUri = $state('');
  let selectedCode = $state('');
  let copied = $state(false);

  function extractCodeFromUri(uri: string): string {
    const hash = uri.split('#').pop();
    if (hash && /^\d+$/.test(hash)) return hash;
    const parts = uri.split('/');
    return parts[parts.length - 1] || uri;
  }

  function loadCSS(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      link.onload = () => resolve();
      link.onerror = () => reject(new Error('CSS load failed'));
      document.head.appendChild(link);
    });
  }

  function loadJSExec(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Script load failed: ' + url));
      document.head.appendChild(script);
    });
  }

  onMount(async () => {
    try {
      // Load ECT from WHO CDN (local ect.js is a polyfill, not the ECT library)
      await loadCSS('https://icdcdn.who.int/embeddedct/icd11ect-1.8.css');
      await loadJSExec('https://icdcdn.who.int/embeddedct/icd11ect-1.8.js');

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const w = window as any;
      const ect = w.ECT;
      // ECT 1.8 API: ECT.Handler.configure(settings, callbacks) — two separate args.
      // autoBind hooks the window "load" event, which has already fired in an SPA,
      // so we set autoBind:false and bind the browser manually.
      if (!ect || typeof ect.Handler?.configure !== 'function') {
        loadError = true;
        return;
      }

      ect.Handler.configure(
        {
          apiServerUrl: 'https://id.who.int',
          apiSecured: true,
          source: 'mms',
          language: 'de',
          minorVersion: '2026-01',
          autoBind: false,
        },
        {
          getNewTokenFunction: async () => {
            const resp = await fetch('/api/v1/icd11/token');
            if (!resp.ok) throw new Error('Token fetch failed');
            const data = await resp.json();
            return data.token;
          },
          browserChangedFunction: (data: { iNo: string; uri: string; code: string }) => {
            selectedUri = data.uri;
            selectedCode = data.code || extractCodeFromUri(data.uri);
            copied = false;
          },
          browserLoadedFunction: () => {
            browserLoaded = true;
          },
        }
      );

      ect.Handler.bind('mb-main');
    } catch (err) {
      console.error('ECT load failed:', err);
      loadError = true;
    }
  });

  async function copyCode() {
    if (!selectedCode) return;
    try {
      await navigator.clipboard.writeText(selectedCode);
      copied = true;
      setTimeout(() => (copied = false), 2000);
    } catch {
      const el = document.getElementById('icd11-selected-code');
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    }
  }
</script>

<svelte:head>
  <title>ICD-11 Browser | MedWiss DB</title>
</svelte:head>

<div class="icd11-page">
  <header class="page-header">
    <div class="header-icon">
      <BookOpen size={28} />
    </div>
    <div class="header-content">
      <h1>ICD-11 Browser</h1>
      <p class="subtitle">Klassifikation der Weltgesundheitsorganisation</p>
    </div>
    <a
      href="https://icd.who.int/browse/2026-01/mms/de"
      target="_blank"
      rel="noopener noreferrer"
      class="header-link"
    >
      <ExternalLink size={16} />
      WHO ICD-11 öffnen
    </a>
  </header>

  {#if loadError}
    <div class="icd11-fallback">
      <p>ICD-11 Browser konnte nicht geladen werden.</p>
      <a
        href="https://icd.who.int/browse/2026-01/mms/de"
        target="_blank"
        rel="noopener noreferrer"
        class="btn btn-secondary"
      >
        <ExternalLink size={16} />
        WHO ICD-11 im neuen Tab öffnen
      </a>
    </div>
  {:else}
    <div class="icd11-content">
      {#if !browserLoaded}
        <div class="icd11-loading">
          <div class="spinner"></div>
          <span>ICD-11 Browser wird geladen…</span>
        </div>
      {/if}

      <div class="ctw-eb-window icd11-container" data-ctw-ino="mb-main"></div>

      {#if selectedCode}
        <div class="icd11-selection-bar">
          <div class="selection-info">
            <span class="selection-label">Ausgewählt:</span>
            <code id="icd11-selected-code" class="selection-code">{selectedCode}</code>
            {#if selectedUri}
              <a
                href={selectedUri}
                target="_blank"
                rel="noopener noreferrer"
                class="selection-link"
              >
                <ExternalLink size={12} />
              </a>
            {/if}
          </div>
          <button class="btn btn-small btn-primary" onclick={copyCode}>
            {#if copied}
              <Check size={14} />
              Kopiert
            {:else}
              <Copy size={14} />
              Kopieren
            {/if}
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .icd11-page {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    margin-bottom: var(--space-6);
  }

  .header-link {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    margin-left: auto;
    padding: var(--space-2) var(--space-3);
    color: var(--color-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    font-weight: var(--font-weight-medium);
    text-decoration: none;
    white-space: nowrap;
  }

  .header-link:hover {
    background: var(--color-background-secondary);
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    margin-bottom: var(--space-6);
  }

  .header-icon {
    color: var(--color-primary);
    flex-shrink: 0;
  }

  h1 {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-bold);
    margin: 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: var(--space-1) 0 0;
  }

  .icd11-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .icd11-loading {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-4);
    color: var(--color-text-secondary);
    background: var(--color-background-secondary);
    border-radius: var(--radius-lg);
  }

  .icd11-container {
    min-height: 600px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    background: var(--color-background-primary);
  }

  .icd11-selection-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    background: var(--color-background-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
  }

  .selection-info {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    min-width: 0;
  }

  .selection-label {
    color: var(--color-text-secondary);
    font-size: 0.85em;
    flex-shrink: 0;
  }

  .selection-code {
    font-size: 0.9em;
    background: var(--color-background-primary);
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
  }

  .selection-link {
    color: var(--color-primary);
    flex-shrink: 0;
  }

  .btn-small {
    padding: 4px 10px;
    font-size: 0.85em;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .icd11-fallback {
    text-align: center;
    padding: var(--space-8);
    color: var(--color-text-secondary);
  }

  .icd11-fallback p {
    margin-bottom: var(--space-4);
    font-size: var(--font-size-lg);
  }

  .icd11-fallback .btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }
</style>
