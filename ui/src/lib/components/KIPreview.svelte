<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade, slide } from 'svelte/transition';
  
  export let status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error' = 'idle';
  export let extractedText = '';
  export let errorMessage = '';
  export let progress = 0;
  
  const dispatch = createEventDispatcher<{
    apply: { text: string };
    retry: void;
    dismiss: void;
  }>();
  
  function handleApply() {
    dispatch('apply', { text: extractedText });
  }
  
  function handleRetry() {
    dispatch('retry');
  }
  
  function handleDismiss() {
    dispatch('dismiss');
  }
  
  function getStatusIcon() {
    switch (status) {
      case 'uploading':
      case 'processing':
        return `<svg class="ki-preview__icon ki-preview__icon--spin" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;
      case 'completed':
        return `<svg class="ki-preview__icon ki-preview__icon--success" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
      case 'error':
        return `<svg class="ki-preview__icon ki-preview__icon--error" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
      default:
        return '';
    }
  }
  
  function getStatusText() {
    switch (status) {
      case 'uploading':
        return 'Datei wird hochgeladen...';
      case 'processing':
        return 'KI verarbeitet Dokument...';
      case 'completed':
        return 'Verarbeitung abgeschlossen';
      case 'error':
        return 'Fehler bei der Verarbeitung';
      default:
        return '';
    }
  }
  
</script>

{#if status !== 'idle'}
  <div class="ki-preview" transition:slide={{ duration: 250 }}>
    <div class="ki-preview__header">
      <div class="ki-preview__status">
        {@html getStatusIcon()}
        <span class="ki-preview__status-text">{getStatusText()}</span>
      </div>
      
      {#if status === 'uploading' || status === 'processing'}
        <div class="ki-preview__progress">
          <div class="ki-preview__progress-bar" style="width: {progress}%"></div>
        </div>
        <span class="ki-preview__progress-text">{Math.round(progress)}%</span>
      {/if}
      
      {#if status === 'completed' || status === 'error'}
        <button
          type="button"
          class="ki-preview__close"
          on:click={handleDismiss}
          aria-label="Schließen"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      {/if}
    </div>
    
    {#if status === 'error'}
      <div class="ki-preview__error" transition:fade>
        <p class="ki-preview__error-message">{errorMessage || 'Ein unerwarteter Fehler ist aufgetreten.'}</p>
        <button
          type="button"
          class="ki-preview__retry-btn"
          on:click={handleRetry}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          Erneut versuchen
        </button>
      </div>
    {/if}
    
    {#if status === 'completed'}
      <div class="ki-preview__content" transition:fade>
        {#if extractedText}
          <div class="ki-preview__section">
            <h4 class="ki-preview__section-title">Extrahierter Text</h4>
            <div class="ki-preview__text-content">
              <p class="ki-preview__text">{extractedText}</p>
            </div>
          </div>
        {/if}

        <div class="ki-preview__actions">
          <button
            type="button"
            class="ki-preview__apply-btn"
            on:click={handleApply}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Übernehmen
          </button>
          <button
            type="button"
            class="ki-preview__dismiss-btn"
            on:click={handleDismiss}
          >
            Verwerfen
          </button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .ki-preview {
    background-color: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    overflow: hidden;
  }
  
  .ki-preview__header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-5);
    background: linear-gradient(135deg, var(--color-primary-subtle) 0%, var(--color-accent-subtle) 100%);
    border-bottom: 1px solid var(--color-border);
  }
  
  .ki-preview__status {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex: 1;
  }
  
  /* :global — icons are injected via {@html}, scoped CSS can't reach them */
  :global(.ki-preview__icon) {
    flex-shrink: 0;
  }
  
  :global(.ki-preview__icon--spin) {
    animation: spin 1s linear infinite;
    color: var(--color-primary);
  }
  
  :global(.ki-preview__icon--success) {
    color: var(--color-success);
  }
  
  :global(.ki-preview__icon--error) {
    color: var(--color-error);
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  .ki-preview__status-text {
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }
  
  .ki-preview__progress {
    flex: 1;
    height: 6px;
    background-color: var(--color-gray-200);
    border-radius: var(--radius-full);
    overflow: hidden;
    max-width: 200px;
  }
  
  .ki-preview__progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-accent) 100%);
    border-radius: var(--radius-full);
    transition: width var(--transition-fast);
  }
  
  .ki-preview__progress-text {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-secondary);
    min-width: 40px;
    text-align: right;
  }
  
  .ki-preview__close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background-color: var(--color-background-primary);
    color: var(--color-text-secondary);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  
  .ki-preview__close:hover {
    background-color: var(--color-error-subtle);
    color: var(--color-error);
  }
  
  .ki-preview__error {
    padding: var(--space-5);
    text-align: center;
  }
  
  .ki-preview__error-message {
    color: var(--color-error);
    margin-bottom: var(--space-4);
  }
  
  .ki-preview__retry-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--color-error);
    background-color: var(--color-error-subtle);
    color: var(--color-error);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  
  .ki-preview__retry-btn:hover {
    background-color: var(--color-error);
    color: var(--color-white);
  }
  
  .ki-preview__content {
    padding: var(--space-5);
  }
  
  .ki-preview__section {
    margin-bottom: var(--space-5);
  }
  
  .ki-preview__section:last-of-type {
    margin-bottom: 0;
  }
  
  .ki-preview__section-title {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-semibold);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-secondary);
    margin-bottom: var(--space-2);
  }
  
  .ki-preview__text {
    font-size: var(--font-size-base);
    color: var(--color-text-primary);
    line-height: var(--line-height-relaxed);
  }
  
  .ki-preview__text-content {
    background-color: var(--color-background-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    max-height: 200px;
    overflow-y: auto;
  }
  
  .ki-preview__actions {
    display: flex;
    gap: var(--space-3);
    margin-top: var(--space-6);
    padding-top: var(--space-5);
    border-top: 1px solid var(--color-border);
  }
  
  .ki-preview__apply-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-5);
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: var(--color-white);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    box-shadow: var(--shadow-md);
  }
  
  .ki-preview__apply-btn:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-lg);
  }
  
  .ki-preview__dismiss-btn {
    display: inline-flex;
    align-items: center;
    padding: var(--space-3) var(--space-5);
    background-color: transparent;
    color: var(--color-text-secondary);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }
  
  .ki-preview__dismiss-btn:hover {
    background-color: var(--color-background-tertiary);
    color: var(--color-text-primary);
  }
</style>
