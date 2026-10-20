<script lang="ts">
  import { Shield, Tag, Loader2, Terminal } from 'lucide-svelte';
  import { onMount } from 'svelte';
  import {
    adminApi,
    classificationsApi,
    type ClassifyFromFilenameResult,
    type FachgebietResponse,
    type DiagnoseResponse,
    type SymptomResponse,
    type DokumenttypResponse,
    type OrdnerLabelResponse
  } from '$lib/api';

  // Appearance settings
  let darkMode = $state(
    typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark'
  );

  $effect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light';
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  });

  // Classify from filename
  let classifyDryRun = $state(true);
  let classifyForce = $state(false);
  let classifying = $state(false);
  let classifyResult = $state<ClassifyFromFilenameResult | null>(null);
  let classifyError = $state<string | null>(null);
  let classifyLog = $state<string[]>([]);

  // Label manager state
  type LabelTab = 'fach' | 'diagnose' | 'symptom' | 'dokumenttyp' | 'ordner';
  let labelTab = $state<LabelTab>('fach');
  let fachgebiete = $state<FachgebietResponse[]>([]);
  let diagnosen = $state<DiagnoseResponse[]>([]);
  let symptome = $state<SymptomResponse[]>([]);
  let dokumenttypen = $state<DokumenttypResponse[]>([]);
  let ordnerLabels = $state<OrdnerLabelResponse[]>([]);
  let labelsLoading = $state(false);
  let labelsError = $state<string | null>(null);
  // add-form state
  let addName = $state('');
  let addCode = $state('');
  // editing state: {id, name, code} or null
  let editingLabel = $state<{ kind: LabelTab; id: number; name: string; code: string } | null>(null);

  async function loadLabels() {
    labelsLoading = true;
    labelsError = null;
    try {
      const [f, d, s, t, o] = await Promise.all([
        classificationsApi.getFachgebiete(),
        classificationsApi.getDiagnosen(),
        classificationsApi.getSymptome(),
        classificationsApi.getDokumenttypen(),
        classificationsApi.getOrdnerLabels()
      ]);
      fachgebiete = f;
      diagnosen = d;
      symptome = s;
      dokumenttypen = t;
      ordnerLabels = o;
    } catch (err: unknown) {
      labelsError = err instanceof Error ? err.message : 'Labels konnten nicht geladen werden';
    } finally {
      labelsLoading = false;
    }
  }

  function startEdit(item: { kind: LabelTab; id: number; name: string; code: string }) {
    editingLabel = { ...item };
    addName = '';
    addCode = '';
  }

  function cancelEdit() {
    editingLabel = null;
    addName = '';
    addCode = '';
  }

  async function handleAddLabel() {
    if (!addName.trim()) return;
    try {
      if (labelTab === 'fach') {
        const created = await classificationsApi.createFachgebiet({ name: addName.trim() });
        fachgebiete = [...fachgebiete, created];
      } else if (labelTab === 'diagnose') {
        const created = await classificationsApi.createDiagnose({ code: addCode.trim() || 'Z99', name: addName.trim() });
        diagnosen = [...diagnosen, created];
      } else if (labelTab === 'symptom') {
        const created = await classificationsApi.createSymptom({ name: addName.trim() });
        symptome = [...symptome, created];
      } else if (labelTab === 'dokumenttyp') {
        const created = await classificationsApi.createDokumenttyp({ name: addName.trim() });
        dokumenttypen = [...dokumenttypen, created];
      } else {
        const created = await classificationsApi.createOrdnerLabel({ name: addName.trim() });
        ordnerLabels = [...ordnerLabels, created];
      }
      addName = '';
      addCode = '';
    } catch (err: unknown) {
      labelsError = err instanceof Error ? err.message : 'Hinzufügen fehlgeschlagen';
    }
  }

  async function handleSaveEdit() {
    if (!editingLabel) return;
    const { kind, id } = editingLabel;
    const name = editingLabel.name.trim();
    const code = editingLabel.code.trim();
    if (!name) return;
    try {
      if (kind === 'fach') {
        const updated = await classificationsApi.updateFachgebiet(id, { name });
        fachgebiete = fachgebiete.map(f => f.id === id ? { ...f, ...updated } : f);
      } else if (kind === 'diagnose') {
        const updated = await classificationsApi.updateDiagnose(id, { name, code: code || undefined });
        diagnosen = diagnosen.map(d => d.id === id ? { ...d, ...updated } : d);
      } else if (kind === 'symptom') {
        const updated = await classificationsApi.updateSymptom(id, { name });
        symptome = symptome.map(s => s.id === id ? { ...s, ...updated } : s);
      } else if (kind === 'dokumenttyp') {
        const updated = await classificationsApi.updateDokumenttyp(id, { name });
        dokumenttypen = dokumenttypen.map(t => t.id === id ? { ...t, ...updated } : t);
      } else {
        const updated = await classificationsApi.updateOrdnerLabel(id, { name });
        ordnerLabels = ordnerLabels.map(l => l.id === id ? { ...l, ...updated } : l);
      }
      editingLabel = null;
    } catch (err: unknown) {
      labelsError = err instanceof Error ? err.message : 'Speichern fehlgeschlagen';
    }
  }

  async function handleDeleteLabel(kind: LabelTab, id: number) {
    if (!confirm('Wirklich löschen? Diese Aktion ist dauerhaft.')) return;
    try {
      if (kind === 'fach') {
        await classificationsApi.deleteFachgebiet(id);
        fachgebiete = fachgebiete.filter(f => f.id !== id);
      } else if (kind === 'diagnose') {
        await classificationsApi.deleteDiagnose(id);
        diagnosen = diagnosen.filter(d => d.id !== id);
      } else if (kind === 'symptom') {
        await classificationsApi.deleteSymptom(id);
        symptome = symptome.filter(s => s.id !== id);
      } else if (kind === 'dokumenttyp') {
        await classificationsApi.deleteDokumenttyp(id);
        dokumenttypen = dokumenttypen.filter(t => t.id !== id);
      } else {
        await classificationsApi.deleteOrdnerLabel(id);
        ordnerLabels = ordnerLabels.filter(l => l.id !== id);
      }
    } catch (err: unknown) {
      labelsError = err instanceof Error ? err.message : 'Löschen fehlgeschlagen';
    }
  }

  function addLog(msg: string) {
    const ts = new Date().toLocaleTimeString('de-DE');
    classifyLog = [...classifyLog, `[${ts}] ${msg}`];
  }

  async function handleClassify() {
    if (classifying) return;
    classifying = true;
    classifyError = null;
    classifyResult = null;
    classifyLog = [];

    const mode = classifyDryRun ? 'Dry Run' : 'Live';
    const scope = classifyForce ? 'Alle Eintraege' : 'Nur unklassifizierte';
    addLog(`Klassifizierung gestartet (${mode}, ${scope})`);
    addLog('Regex-Abgleich: Fachgebiet aus Ordner, Diagnose/Symptom aus Dateiname. Kein LLM.');
    addLog('ICD-11-Codes werden anschliessend ueber die WHO API ergaenzt (wenn konfiguriert).');

    try {
      classifyResult = await adminApi.classifyFromFilename({
        force: classifyForce,
        dry_run: classifyDryRun,
      });
      addLog(`Fertig: ${classifyResult.fachgebiete_assigned} Fachgebiete, ${classifyResult.diagnosen_assigned} Diagnosen, ${classifyResult.symptome_assigned} Symptome, ${classifyResult.icd11_enriched} ICD-11`);
    } catch (err: unknown) {
      classifyError = err instanceof Error ? err.message : 'Klassifizierung fehlgeschlagen';
      addLog(`FEHLER: ${classifyError}`);
    } finally {
      classifying = false;
    }
  }

  onMount(() => { loadLabels(); });
</script>

<svelte:head>
  <title>Admin | MedWiss DB</title>
</svelte:head>

<div class="admin-page">
  <header class="page-header">
    <div class="header-icon">
      <Shield size={28} />
    </div>
    <div class="header-content">
      <h1>Administration</h1>
    </div>
  </header>

  <div class="admin-container">
    <section class="settings-section">
      <label class="toggle-inline">
        <div class="toggle-content">
          <span class="toggle-label">Dark Mode</span>
          <span class="toggle-description">Dunkles Farbschema verwenden</span>
        </div>
        <input
          type="checkbox"
          bind:checked={darkMode}
          class="toggle-input"
        />
      </label>
    </section>

    <!-- Dateinamen-Klassifizierung -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon">
          <Tag size={20} />
        </div>
        <div class="section-title">
          <h2>Automatische Klassifizierung</h2>
          <p class="section-description">Regex-Abgleich: Fachgebiet aus Ordner, Diagnose/Symptom aus Dateiname. Kein LLM.</p>
        </div>
      </div>

      <div class="classify-controls">
        <div class="settings-grid">
          <div class="form-field">
            <label class="toggle-inline">
              <div class="toggle-content">
                <span class="toggle-label">Nur unklassifizierte</span>
                <span class="toggle-description">Nur Einträge ohne Diagnosen bearbeiten</span>
              </div>
              <input
                type="checkbox"
                checked={!classifyForce}
                onchange={() => classifyForce = !classifyForce}
                class="toggle-input"
              />
            </label>
          </div>

          <div class="form-field">
            <label class="toggle-inline">
              <div class="toggle-content">
                <span class="toggle-label">Dry Run</span>
                <span class="toggle-description">Nur Vorschau, keine Änderungen in der DB</span>
              </div>
              <input
                type="checkbox"
                bind:checked={classifyDryRun}
                class="toggle-input"
              />
            </label>
          </div>
        </div>

        <div class="action-buttons">
          <button
            class="btn btn-primary"
            onclick={handleClassify}
            disabled={classifying}
          >
            {#if classifying}
              <Loader2 size={18} class="spin" />
              Klassifizierung läuft...
            {:else}
              <Tag size={18} />
              Klassifizieren
            {/if}
          </button>
        </div>
      </div>

      {#if classifyError}
        <div class="classify-alert error">
          <span>{classifyError}</span>
        </div>
      {/if}

      {#if classifyResult}
        <div class="classify-result">
          <h3>Ergebnis {classifyResult.dry_run ? '(Dry Run)' : ''}</h3>
          <div class="result-grid">
            <div class="result-item">
              <span class="result-label">Gesamt</span>
              <span class="result-value">{classifyResult.total_entries}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Fachgebiete</span>
              <span class="result-value success">{classifyResult.fachgebiete_assigned}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Diagnosen</span>
              <span class="result-value success">{classifyResult.diagnosen_assigned}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Symptome</span>
              <span class="result-value">{classifyResult.symptome_assigned}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Einträge</span>
              <span class="result-value">{classifyResult.entries_touched}</span>
            </div>
            <div class="result-item">
              <span class="result-label">ICD-11</span>
              <span class="result-value">{classifyResult.icd11_enriched}</span>
            </div>
          </div>
        </div>
      {/if}

      <!-- Live Log -->
      {#if classifyLog.length > 0}
        <div class="classify-log">
          <div class="log-header">
            <Terminal size={16} />
            <span>Live-Log</span>

          </div>
          <div class="log-body">
            {#each classifyLog as line}
              <div class="log-line">{line}</div>
            {/each}
          </div>
        </div>
      {/if}
    </section>


    <!-- Label-Verwaltung -->
    <section class="settings-section">
      <div class="section-header">
        <div class="section-icon">
          <Tag size={20} />
        </div>
        <div class="section-title">
          <h2>Labels verwalten</h2>
          <p class="section-description">Fachgebiete, Diagnosen, Symptome, Dokumenttypen und Ordner-Labels anlegen, umbenennen oder löschen</p>
        </div>
      </div>

      <div class="label-tabs">
        <button
          class="label-tab {labelTab === 'fach' ? 'active' : ''}"
          onclick={() => { labelTab = 'fach'; cancelEdit(); }}
        >Fachgebiete ({fachgebiete.length})</button>
        <button
          class="label-tab {labelTab === 'diagnose' ? 'active' : ''}"
          onclick={() => { labelTab = 'diagnose'; cancelEdit(); }}
        >Diagnosen ({diagnosen.length})</button>
        <button
          class="label-tab {labelTab === 'symptom' ? 'active' : ''}"
          onclick={() => { labelTab = 'symptom'; cancelEdit(); }}
        >Symptome ({symptome.length})</button>
        <button
          class="label-tab {labelTab === 'dokumenttyp' ? 'active' : ''}"
          onclick={() => { labelTab = 'dokumenttyp'; cancelEdit(); }}
        >Dokumenttypen ({dokumenttypen.length})</button>
        <button
          class="label-tab {labelTab === 'ordner' ? 'active' : ''}"
          onclick={() => { labelTab = 'ordner'; cancelEdit(); }}
        >Ordner-Labels ({ordnerLabels.length})</button>
      </div>

      {#if labelsLoading}
        <div class="label-status"><span class="spinner"></span> Lädt...</div>
      {:else if labelsError}
        <div class="classify-alert error"><span>{labelsError}</span></div>
      {:else}
        <div class="label-add">
          {#if labelTab === 'diagnose'}
            <input
              type="text"
              bind:value={addCode}
              class="field-input label-code-input"
            />
          {/if}
          <input
            type="text"
            bind:value={addName}
            class="field-input"
            onkeydown={(e) => { if (e.key === 'Enter') handleAddLabel(); }}
          />
          <button class="btn btn-secondary" onclick={handleAddLabel} disabled={!addName.trim()}>
            Hinzufügen
          </button>
        </div>
        {/if}

        <div class="label-list">
          {#if labelTab === 'fach'}
            {#each fachgebiete as f (f.id)}
              <div class="label-row">
                {#if editingLabel?.kind === 'fach' && editingLabel.id === f.id}
                  <input type="text" bind:value={editingLabel.name} class="field-input" />
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={handleSaveEdit}>Speichern</button>
                    <button class="btn btn-small" onclick={cancelEdit}>Abbruch</button>
                  </div>
                {:else}
                  <span class="label-name">{f.name}</span>
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={() => startEdit({ kind: 'fach', id: f.id, name: f.name, code: '' })}>Umbenennen</button>
                    <button class="btn btn-small btn-danger" onclick={() => handleDeleteLabel('fach', f.id)}>Löschen</button>
                  </div>
                {/if}
              </div>
            {/each}
          {:else if labelTab === 'diagnose'}
            {#each diagnosen as d (d.id)}
              <div class="label-row">
                {#if editingLabel?.kind === 'diagnose' && editingLabel.id === d.id}
                  <input type="text" bind:value={editingLabel.code} class="field-input label-code-input" />
                  <input type="text" bind:value={editingLabel.name} class="field-input" />
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={handleSaveEdit}>Speichern</button>
                    <button class="btn btn-small" onclick={cancelEdit}>Abbruch</button>
                  </div>
                {:else}
                  <span class="label-name">
                    {#if d.code}<code class="label-code">{d.code}</code>{/if}
                    {d.name}
                    {#if d.icd11_code}<span class="label-icd11" title="ICD-11">{d.icd11_code}</span>{/if}
                  </span>
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={() => startEdit({ kind: 'diagnose', id: d.id, name: d.name, code: d.code })}>Umbenennen</button>
                    <button class="btn btn-small btn-danger" onclick={() => handleDeleteLabel('diagnose', d.id)}>Löschen</button>
                  </div>
                {/if}
              </div>
            {/each}
          {:else if labelTab === 'dokumenttyp'}
            {#each dokumenttypen as t (t.id)}
              <div class="label-row">
                {#if editingLabel?.kind === 'dokumenttyp' && editingLabel.id === t.id}
                  <input type="text" bind:value={editingLabel.name} class="field-input" />
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={handleSaveEdit}>Speichern</button>
                    <button class="btn btn-small" onclick={cancelEdit}>Abbruch</button>
                  </div>
                {:else}
                  <span class="label-name">
                    {t.name}
                    {#if t.needs_review}<span class="label-icd11" title="Auto-created, pending review">Review</span>{/if}
                  </span>
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={() => startEdit({ kind: 'dokumenttyp', id: t.id, name: t.name, code: '' })}>Umbenennen</button>
                    <button class="btn btn-small btn-danger" onclick={() => handleDeleteLabel('dokumenttyp', t.id)}>Löschen</button>
                  </div>
                {/if}
              </div>
            {/each}
          {:else if labelTab === 'ordner'}
            {#each ordnerLabels as l (l.id)}
              <div class="label-row">
                {#if editingLabel?.kind === 'ordner' && editingLabel.id === l.id}
                  <input type="text" bind:value={editingLabel.name} class="field-input" />
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={handleSaveEdit}>Speichern</button>
                    <button class="btn btn-small" onclick={cancelEdit}>Abbruch</button>
                  </div>
                {:else}
                  <span class="label-name">
                    {l.name}
                    {#if l.needs_review}<span class="label-icd11" title="Auto-created, pending review">Review</span>{/if}
                  </span>
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={() => startEdit({ kind: 'ordner', id: l.id, name: l.name, code: '' })}>Umbenennen</button>
                    <button class="btn btn-small btn-danger" onclick={() => handleDeleteLabel('ordner', l.id)}>Löschen</button>
                  </div>
                {/if}
              </div>
            {/each}
          {:else}
            {#each symptome as s (s.id)}
              <div class="label-row">
                {#if editingLabel?.kind === 'symptom' && editingLabel.id === s.id}
                  <input type="text" bind:value={editingLabel.name} class="field-input" />
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={handleSaveEdit}>Speichern</button>
                    <button class="btn btn-small" onclick={cancelEdit}>Abbruch</button>
                  </div>
                {:else}
                  <span class="label-name">{s.name}</span>
                  <div class="label-row-actions">
                    <button class="btn btn-small" onclick={() => startEdit({ kind: 'symptom', id: s.id, name: s.name, code: '' })}>Umbenennen</button>
                    <button class="btn btn-small btn-danger" onclick={() => handleDeleteLabel('symptom', s.id)}>Löschen</button>
                  </div>
                {/if}
              </div>
            {/each}
          {/if}
        </div>
    </section>
  </div>
</div>

<style>
  .admin-page {
    max-width: 1000px;
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }

  .page-header {
    display: flex;
    align-items: center;
    gap: var(--space-4);
  }

  .header-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: var(--color-primary);
    color: white;
    border-radius: var(--radius-lg);
    flex-shrink: 0;
  }

  .header-content h1 {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-1);
  }

  .admin-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
  }

  .settings-section {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    overflow: hidden;
  }

  .section-header {
    display: flex;
    align-items: flex-start;
    gap: var(--space-4);
    padding: var(--space-6);
    background: var(--color-background-secondary);
    border-bottom: 1px solid var(--color-border);
  }

  .section-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: var(--color-primary);
    color: white;
    border-radius: var(--radius-lg);
    flex-shrink: 0;
  }

  .section-title h2 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-1);
  }

  .section-description {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--space-5);
    padding: var(--space-6);
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .field-input {
    padding: var(--space-3) var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    font-size: var(--font-size-base);
    color: var(--color-text-primary);
    background: var(--color-background-primary);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .field-input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: var(--shadow-focus);
  }

  .settings-section > .toggle-inline {
    padding: var(--space-4) var(--space-6);
  }

  .toggle-inline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
    padding: var(--space-3) 0;
    cursor: pointer;
  }

  .toggle-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .toggle-label {
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }

  .toggle-description {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }

  .toggle-input {
    appearance: none;
    width: 48px;
    height: 26px;
    background: var(--color-border);
    border-radius: var(--radius-full);
    position: relative;
    cursor: pointer;
    transition: background var(--transition-fast);
    flex-shrink: 0;
  }

  .toggle-input::after {
    content: '';
    position: absolute;
    width: 22px;
    height: 22px;
    background: white;
    border-radius: 50%;
    top: 2px;
    left: 2px;
    transition: transform var(--transition-fast);
    box-shadow: var(--shadow-sm);
  }

  .toggle-input:checked {
    background: var(--color-primary);
  }

  .toggle-input:checked::after {
    transform: translateX(22px);
  }

  .action-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    padding: 0 var(--space-6) var(--space-6);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-5);
    border-radius: var(--radius-lg);
    font-weight: var(--font-weight-medium);
    font-size: var(--font-size-base);
    cursor: pointer;
    transition: all var(--transition-fast);
    text-decoration: none;
    border: none;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--color-primary-dark);
  }

  .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: transparent;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover {
    background: var(--color-background-tertiary);
    color: var(--color-text-primary);
  }

  .classify-controls {
    padding: var(--space-4) var(--space-6);
  }

  .classify-alert {
    padding: var(--space-3) var(--space-6);
    font-size: var(--font-size-sm);
  }

  .classify-alert.error {
    background: #fef2f2;
    color: #991b1b;
    border-top: 1px solid #fecaca;
  }

  .classify-result {
    padding: var(--space-4) var(--space-6) var(--space-6);
  }

  .classify-result h3 {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--space-3);
  }

  .result-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: var(--space-3);
  }

  .result-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-3);
    background: var(--color-background-secondary);
    border-radius: var(--radius-lg);
  }

  .result-label {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .result-value {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
  }

  .result-value.success {
    color: #059669;
  }


  .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  :global(.spin) {
    animation: spin 0.8s linear infinite;
  }

  @media (max-width: 768px) {
    .admin-page {
      padding: var(--space-4);
    }

    .page-header {
      flex-direction: column;
      gap: var(--space-3);
    }

    .header-content h1 {
      font-size: var(--font-size-2xl);
    }

    .settings-grid {
      grid-template-columns: 1fr;
    }

    .section-header {
      flex-direction: column;
      gap: var(--space-3);
    }


    .result-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  .classify-log {
    border-top: 1px solid var(--color-border);
  }
  .log-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-6);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-secondary);
    background: var(--color-background-secondary);
    border-bottom: 1px solid var(--color-border);
  }
  .log-body {
    max-height: 250px;
    overflow-y: auto;
    padding: var(--space-2) var(--space-6);
    font-family: monospace;
    font-size: var(--font-size-xs);
    line-height: 1.6;
    color: var(--color-text-secondary);
    background: var(--color-background-primary);
  }
  .log-line {
    white-space: pre-wrap;
    word-break: break-all;
  }

  /* Label-Verwaltung */
  .label-tabs {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
    border-bottom: 1px solid var(--color-border);
  }
  .label-tab {
    padding: var(--space-2) var(--space-4);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    color: var(--color-text-secondary);
    font-weight: var(--font-weight-medium);
  }
  .label-tab.active {
    color: var(--color-primary);
    border-bottom-color: var(--color-primary);
  }
  .label-add {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
  }
  .label-add .field-input {
    flex: 1;
  }
  .label-code-input {
    max-width: 140px;
    flex: 0 0 140px;
  }
  .label-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    max-height: 420px;
    overflow-y: auto;
  }
  .label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }
  .label-row .field-input {
    flex: 1;
  }
  .label-name {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: 1;
  }
  .label-code {
    background: var(--color-background-secondary);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.85em;
  }
  .label-icd11 {
    font-size: 0.75em;
    color: var(--color-primary);
    border: 1px solid var(--color-primary);
    border-radius: var(--radius-sm);
    padding: 1px 5px;
  }
  .label-row-actions {
    display: flex;
    gap: var(--space-1);
    flex-shrink: 0;
  }
  .btn-small {
    padding: 4px 10px;
    font-size: 0.85em;
  }
  .btn-danger {
    background: var(--color-danger, #dc2626);
    color: #fff;
  }
  .btn-danger:hover {
    background: #b91c1c;
  }
  .label-status {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--color-text-secondary);
  }
</style>
