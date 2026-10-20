<script lang="ts">
  import { fade } from 'svelte/transition';
  import { apiClient } from '$lib/api';
  import { X, Loader2, Check, AlertCircle, RefreshCw, Copy, ScanText } from 'lucide-svelte';

  interface Props {
    entryId: number;
    open?: boolean;
    oncancel: () => void;
  }

  let { entryId, open = false, oncancel }: Props = $props();

  let status: 'idle' | 'processing' | 'completed' | 'error' = $state('idle');
  let extractedText = $state('');
  let error = $state<string | null>(null);
  let copied = $state(false);

  // OCR engine override. null = Auto (OCR_BACKENDS order: Tesseract → glm-4.6v).
  const backends = [
    { id: '', label: 'Automatisch', hint: 'Tesseract, dann glm-4.6v bei Fehler' },
    { id: 'tesseract', label: 'Tesseract (lokal)', hint: 'Schnell, offline' },
    { id: 'openrouter-vision', label: 'glm-4.6v (OpenRouter)', hint: 'Genauer bei Scans' }
  ];
  let selectedBackend = $state('');

  async function startTranscription() {
    status = 'processing';
    error = null;
    copied = false;
    try {
      const response = await apiClient.post(`/entries/${entryId}/transcribe`, {
        backend: selectedBackend || null
      });
      extractedText = response.data.extracted_text || '';
      status = 'completed';
    } catch (err: any) {
      error = err?.response?.data?.detail || err.message || 'Fehler bei der Transkription';
      status = 'error';
    }
  }

  async function copyText() {
    try {
      await navigator.clipboard.writeText(extractedText);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      copied = false;
    }
  }

  function handleRetry() {
    status = 'idle';
    error = null;
  }

  function handleClose() {
    status = 'idle';
    extractedText = '';
    oncancel();
  }
</script>

{#if open}
<div class="modal-overlay" transition:fade={{ duration: 200 }}>
  <div class="modal-container">
    <div class="modal-header">
      <div class="header-left">
        <h2 class="modal-title">
          {#if status === 'processing'}
            <span class="title-icon spinning"><Loader2 size={20} /></span>
          {:else if status === 'completed'}
            <span class="title-icon success"><Check size={20} /></span>
          {:else if status === 'error'}
            <span class="title-icon error"><AlertCircle size={20} /></span>
          {:else}
            <span class="title-icon"><ScanText size={20} /></span>
          {/if}
          Transkribieren
        </h2>
      </div>
      <button type="button" class="close-btn" onclick={handleClose} aria-label="Schließen">
        <X size={20} />
      </button>
    </div>

    {#if status === 'processing'}
      <div class="processing-section">
        <span class="status-text">Text wird extrahiert…</span>
      </div>
    {/if}

    {#if status !== 'processing'}
      <div class="selector-row">
        <label class="selector-label" for="transcribe-backend">OCR-Motor</label>
        <select
          id="transcribe-backend"
          class="selector"
          bind:value={selectedBackend}
        >
          {#each backends as b (b.id)}
            <option value={b.id}>{b.label}</option>
          {/each}
        </select>
        <span class="selector-hint">
          {backends.find((b) => b.id === selectedBackend)?.hint}
        </span>
      </div>
    {/if}

    {#if status === 'error'}
      <div class="error-section">
        <div class="error-icon"><AlertCircle size={32} /></div>
        <p class="error-message">{error}</p>
        <button type="button" class="retry-btn" onclick={handleRetry}>
          <RefreshCw size={16} /> Erneut versuchen
        </button>
      </div>
    {/if}

    {#if status === 'completed'}
      <div class="content-section">
        <textarea class="transcribed-text" readonly value={extractedText}></textarea>
      </div>
    {/if}

    {#if status === 'idle'}
      <div class="idle-section">
        <span class="status-text">
          Wähle einen OCR-Motor und starte die Textextraktion.
        </span>
      </div>
    {/if}

    <div class="modal-footer">
      <button type="button" class="btn btn-secondary" onclick={handleClose}>Schließen</button>
      {#if status === 'idle'}
        <button type="button" class="btn btn-primary" onclick={startTranscription}>
          <ScanText size={16} /> Transkribieren
        </button>
      {:else}
        <button
          type="button"
          class="btn btn-primary"
          onclick={copyText}
          disabled={status !== 'completed' || !extractedText}
        >
          <Copy size={16} />
          {copied ? 'Kopiert!' : 'Kopieren'}
        </button>
      {/if}
    </div>
  </div>
</div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: var(--space-4);
  }

  .modal-container {
    background-color: var(--color-background-primary);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    width: 100%;
    max-width: 900px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    padding: var(--space-4) var(--space-6);
    background: linear-gradient(135deg, var(--color-primary-subtle) 0%, var(--color-accent-subtle) 100%);
    border-bottom: 1px solid var(--color-border);
  }

  .modal-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin: 0;
  }

  .title-icon {
    display: inline-flex;
    flex-shrink: 0;
  }

  .title-icon.spinning {
    animation: spin 1s linear infinite;
    color: var(--color-primary);
  }

  .title-icon.success {
    color: var(--color-success);
  }

  .title-icon.error {
    color: var(--color-error);
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border: none;
    background-color: var(--color-background-primary);
    color: var(--color-text-secondary);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }

  .close-btn:hover {
    background-color: var(--color-error-subtle);
    color: var(--color-error);
  }

  .processing-section {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-12);
    gap: var(--space-3);
  }

  .status-text {
    color: var(--color-text-secondary);
    font-size: var(--font-size-md);
  }

  .selector-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-6);
    border-bottom: 1px solid var(--color-border);
    flex-wrap: wrap;
  }

  .selector-label {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    font-weight: var(--font-weight-medium);
  }

  .selector {
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background-color: var(--color-background-primary);
    color: var(--color-text-primary);
    font-size: var(--font-size-sm);
    cursor: pointer;
  }

  .selector-hint {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary, var(--color-text-secondary));
  }

  .idle-section {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-12);
    gap: var(--space-3);
  }

  .error-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-12);
    gap: var(--space-4);
  }

  .error-icon {
    color: var(--color-error);
  }

  .error-message {
    color: var(--color-error);
    text-align: center;
    max-width: 480px;
  }

  .retry-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--color-error);
    background-color: var(--color-error-subtle);
    color: var(--color-error);
    font-size: var(--font-size-sm);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .content-section {
    padding: var(--space-4) var(--space-6);
    overflow-y: auto;
    flex: 1;
  }

  .transcribed-text {
    width: 100%;
    min-height: 360px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    font-family: var(--font-mono, monospace);
    font-size: var(--font-size-sm);
    line-height: 1.6;
    background-color: var(--color-background-primary);
    color: var(--color-text-primary);
    resize: vertical;
    white-space: pre-wrap;
  }

  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-6);
    border-top: 1px solid var(--color-border);
    background-color: var(--color-background-secondary);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-5);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    cursor: pointer;
    border: 1px solid transparent;
    transition: all var(--transition-fast);
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background-color: var(--color-background-primary);
    color: var(--color-text-primary);
    border-color: var(--color-border);
  }

  .btn-secondary:hover:not(:disabled) {
    background-color: var(--color-gray-100);
  }

  .btn-primary {
    background-color: var(--color-primary);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background-color: var(--color-primary-dark);
  }

  @media (max-width: 768px) {
    .modal-overlay {
      padding: var(--space-2);
    }
    .modal-footer {
      flex-direction: column-reverse;
    }
    .btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>
