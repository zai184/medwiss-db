<script lang="ts">
  import { onMount } from 'svelte';
  import { Plus, ArrowLeft, Save, FileText, Sparkles } from 'lucide-svelte';
  import { entriesApi, classificationsApi, pipelineApi, type EntryCreate } from '$lib/api';
  import { goto } from '$app/navigation';
  import FileUpload from '$lib/components/FileUpload.svelte';
  import MultiSelect from '$lib/components/MultiSelect.svelte';
  import KIPreview from '$lib/components/KIPreview.svelte';

  // Form state
  let titel = $state('');
  let zusammenfassung = $state('');
  let inhalt = $state('');
  let quelle = $state('');
  let dokumenttypId: number | null = $state(null);
  let schwierigkeit = $state('');
  let selectedFachgebiete: number[] = $state([]);
  let selectedDiagnosen: number[] = $state([]);
  let selectedSymptome: number[] = $state([]);
  let selectedOrdnerLabels: number[] = $state([]);

  let fachgebiete = $state<{id: number, name: string}[]>([]);
  let diagnosen = $state<{id: number, name: string, code: string}[]>([]);
  let symptome = $state<{id: number, name: string}[]>([]);
  let dokumenttypen = $state<{id: number, name: string}[]>([]);
  let ordnerLabels = $state<{id: number, name: string}[]>([]);
  
  let saving = $state(false);
  let error = $state<string | null>(null);

  // KI processing state
  let kiStatus: 'idle' | 'uploading' | 'processing' | 'completed' | 'error' = $state('idle');
  let kiProgress = $state(0);
  let kiExtractedText = $state('');
  let kiErrorMessage = $state('');



  onMount(async () => {
    try {
      const [fachResponse, diagResponse, sympResponse, typResponse, labelResponse] = await Promise.all([
        classificationsApi.getFachgebiete(),
        classificationsApi.getDiagnosen(),
        classificationsApi.getSymptome(),
        classificationsApi.getDokumenttypen(),
        classificationsApi.getOrdnerLabels()
      ]);
      fachgebiete = fachResponse;
      diagnosen = diagResponse;
      symptome = sympResponse;
      dokumenttypen = typResponse;
      ordnerLabels = labelResponse;
    } catch (err) {
      console.error('Failed to load classifications:', err);
    }
  });

  async function handleSubmit(event: Event) {
    event.preventDefault();
    
    console.log('Submit clicked - titel:', titel, 'inhalt:', inhalt, 'length:', inhalt.length);
    
    if (!titel.trim() || !inhalt.trim()) {
      error = 'Titel und Inhalt sind erforderlich - bitte füllen Sie die Felder aus oder klicken Sie "Übernehmen"';
      return;
    }

    try {
      saving = true;
      error = null;

      const entryData: EntryCreate = {
        titel,
        zusammenfassung: zusammenfassung || null,
        inhalt,
        quelle: quelle || null,
        dokumenttyp_id: dokumenttypId,
        schwierigkeit: schwierigkeit || null,
        fachgebiet_ids: selectedFachgebiete,
        diagnose_ids: selectedDiagnosen,
        symptom_ids: selectedSymptome,
        ordner_label_ids: selectedOrdnerLabels
      };

      await entriesApi.create(entryData);
      goto('/');
    } catch (err) {
      console.error('Failed to save entry:', err);
      error = 'Fehler beim Speichern des Eintrags';
    } finally {
      saving = false;
    }
  }

  async function handleFileUpload(event: CustomEvent<{ file: File; progress: number }>) {
    const { file } = event.detail;
    
    kiStatus = 'processing';
    kiProgress = 0;
    
    const steps = [
      { progress: 25, delay: 800 },
      { progress: 50, delay: 1500 },
      { progress: 75, delay: 1200 },
      { progress: 100, delay: 1000 }
    ];
    
    let currentStep = 0;
    
    function processNextStep() {
      if (currentStep < steps.length) {
        setTimeout(() => {
          kiProgress = steps[currentStep].progress;
          currentStep++;
          processNextStep();
        }, steps[currentStep].delay);
      }
    }
    
    processNextStep();
    await completeKIProcessing(file);
  }
  
  async function completeKIProcessing(file: File) {
    try {
      kiStatus = 'processing';
      kiProgress = 10;

      const result = await pipelineApi.processFile(file);

      kiProgress = 100;

      if (result.success) {
        kiExtractedText = result.extracted_text || '';
        kiStatus = 'completed';
      } else {
        kiErrorMessage = 'Verarbeitung fehlgeschlagen';
        kiStatus = 'error';
      }
    } catch (error) {
      kiErrorMessage = error instanceof Error ? error.message : 'Unbekannter Fehler';
      kiStatus = 'error';
    }
  }
  
  function handleKIError(event: CustomEvent<{ message: string }>) {
    kiErrorMessage = event.detail.message;
    kiStatus = 'error';
  }
  async function handleKIApply() {
    if (kiExtractedText) inhalt = kiExtractedText;
    kiStatus = 'idle';
    kiExtractedText = '';
  }
  
  function handleKIRetry() {
    kiStatus = 'idle';
    kiProgress = 0;
    kiErrorMessage = '';
  }
  
  function handleKIDismiss() {
    kiStatus = 'idle';
    kiExtractedText = '';
    kiErrorMessage = '';
  }
  async function handleCreateFachgebiet(detail: { value: string }) {
    const name = detail.value.trim();
    if (!name) return;
    try {
      const created = await classificationsApi.createFachgebiet({ name });
      fachgebiete = [...fachgebiete, created];
      selectedFachgebiete = [...selectedFachgebiete, created.id];
    } catch {
      // 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates
      const resolved = await classificationsApi.resolveLabels({
        fachgebiete: [name],
        diagnosen: [],
        symptome: []
      });
      if (resolved.fachgebiet_ids.length > 0) {
        fachgebiete = await classificationsApi.getFachgebiete();
        selectedFachgebiete = [...selectedFachgebiete, resolved.fachgebiet_ids[0]];
      }
    }
  }

  async function handleCreateDiagnose(detail: { value: string }) {
    const name = detail.value.trim();
    if (!name) return;
    try {
      // Resolver creates the row (TEMP code) with needs_review when missing.
      const resolved = await classificationsApi.resolveLabels({ diagnosen: [{ name }] });
      if (resolved.diagnose_ids.length > 0) {
        diagnosen = await classificationsApi.getDiagnosen();
        selectedDiagnosen = [...selectedDiagnosen, resolved.diagnose_ids[0]];
      }
    } catch (err) {
      console.error('Failed to create diagnose:', err);
    }
  }

  async function handleCreateSymptom(detail: { value: string }) {
    const name = detail.value.trim();
    if (!name) return;
    try {
      const created = await classificationsApi.createSymptom({ name });
      symptome = [...symptome, created];
      selectedSymptome = [...selectedSymptome, created.id];
    } catch {
      // 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates
      const resolved = await classificationsApi.resolveLabels({ symptome: [name] });
      if (resolved.symptom_ids.length > 0) {
        symptome = await classificationsApi.getSymptome();
        selectedSymptome = [...selectedSymptome, resolved.symptom_ids[0]];
      }
    }
  }

  async function handleCreateOrdnerLabel(detail: { value: string }) {
    const name = detail.value.trim();
    if (!name) return;
    try {
      const created = await classificationsApi.createOrdnerLabel({ name });
      ordnerLabels = [...ordnerLabels, created];
      selectedOrdnerLabels = [...selectedOrdnerLabels, created.id];
    } catch {
      // 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates
      const resolved = await classificationsApi.resolveLabels({ ordner_labels: [name] });
      if (resolved.ordner_label_ids.length > 0) {
        ordnerLabels = await classificationsApi.getOrdnerLabels();
        selectedOrdnerLabels = [...selectedOrdnerLabels, resolved.ordner_label_ids[0]];
      }
    }
  }

</script>

<svelte:head>
  <title>Neuer Eintrag | MedWiss DB</title>
</svelte:head>


<div class="entry-page">
  <header class="entry-header">
    <h1>Neuer Eintrag</h1>
  </header>

  {#if error}
    <div class="error-banner">
      <span>{error}</span>
    </div>
  {/if}

  <div class="entry-container">
    <div class="entry-content">
      <div class="form-card">
        <div class="card-header ki-header">
          <div class="header-icon">
            <Sparkles size={20} />
          </div>
          <div class="header-content">
            <h2>KI-Unterstützung</h2>
            <p class="header-description">
              Laden Sie ein Dokument hoch für automatische KI-Verarbeitung und Extraktion
            </p>
          </div>
        </div>
        
        <div class="card-body">
          <FileUpload
            label="Fortbildungsmaterial, Screenshot oder Audio"
            description="Ziehen Sie Dateien hierher für automatische KI-Verarbeitung"
            accept=".png,.jpg,.jpeg,.pdf,.mp3,.wav,.m4a,.txt,.md"
            maxSizeMB={50}
            on:upload={handleFileUpload}
            on:error={handleKIError}
          />
          
          <KIPreview
            status={kiStatus}
            progress={kiProgress}
            extractedText={kiExtractedText}
            errorMessage={kiErrorMessage}
            on:apply={handleKIApply}
            on:retry={handleKIRetry}
            on:dismiss={handleKIDismiss}
          />
        </div>
      </div>

      <form onsubmit={handleSubmit} class="form-card">
        <div class="card-header">
          <div class="header-icon">
            <FileText size={20} />
          </div>
          <div class="header-content">
            <h2>Eintrag bearbeiten</h2>
            <p class="header-description">
              Geben Sie die Details des Eintrags ein
            </p>
          </div>
        </div>

        <div class="card-body form-grid">
          <div class="form-field full-width">
            <label for="titel" class="field-label">
              Titel <span class="required">*</span>
            </label>
            <input
              type="text"
              id="titel"
              bind:value={titel}
              class="field-input"
              required
            />
          </div>

          <div class="form-field full-width">
            <label for="zusammenfassung" class="field-label">
              Zusammenfassung
            </label>
            <textarea
              id="zusammenfassung"
              bind:value={zusammenfassung}
              rows="2"
              class="field-input field-textarea"
            ></textarea>
          </div>

          <div class="form-field full-width">
            <label for="inhalt" class="field-label">
              Inhalt <span class="required">*</span>
            </label>
            <textarea
              id="inhalt"
              bind:value={inhalt}
              rows="10"
              class="field-input field-textarea field-monospace"
              required
            ></textarea>
          </div>

          <div class="form-field full-width">
            <label for="quelle" class="field-label">
              Quelle
            </label>
            <input
              type="text"
              id="quelle"
              bind:value={quelle}
              class="field-input"
            />
          </div>

          <div class="form-row">
            <div class="form-field">
              <label for="dokumenttyp" class="field-label">
                Dokumenttyp
              </label>
              <select id="dokumenttyp" bind:value={dokumenttypId} class="field-input field-select">
                <option value={null}>-- Auswählen --</option>
                {#each dokumenttypen as typ (typ.id)}
                  <option value={typ.id}>{typ.name}</option>
                {/each}
              </select>
            </div>

            <div class="form-field">
              <label for="schwierigkeit" class="field-label">
                Schwierigkeit
              </label>
              <select id="schwierigkeit" bind:value={schwierigkeit} class="field-input field-select">
                <option value="">-- Auswählen --</option>
                <option value="anfaenger">Anfänger</option>
                <option value="fortgeschritten">Fortgeschritten</option>
                <option value="experte">Experte</option>
              </select>
            </div>
          </div>

          <div class="form-field full-width">
            <MultiSelect
              label="Fachgebiete"
              options={fachgebiete.map(f => ({ id: f.id, label: f.name }))}
              bind:selected={selectedFachgebiete}
              allowCreate={true}
              createLabel="+ Neues Fachgebiet"
              oncreate={handleCreateFachgebiet}
            />
          </div>

          <div class="form-field full-width">
            <MultiSelect
              label="Diagnosen"
              options={diagnosen.map(d => ({ id: d.id, label: d.name }))}
              bind:selected={selectedDiagnosen}
              allowCreate={true}
              createLabel="+ Neue Diagnose"
              oncreate={handleCreateDiagnose}
            />
          </div>

          <div class="form-field full-width">
            <MultiSelect
              label="Symptome"
              options={symptome.map(s => ({ id: s.id, label: s.name }))}
              bind:selected={selectedSymptome}
              allowCreate={true}
              createLabel="+ Neues Symptom"
              oncreate={handleCreateSymptom}
            />
          </div>

          <div class="form-field full-width">
            <MultiSelect
              label="Ordner-Labels"
              options={ordnerLabels.map(l => ({ id: l.id, label: l.name }))}
              bind:selected={selectedOrdnerLabels}
              allowCreate={true}
              createLabel="+ Neues Ordner-Label"
              oncreate={handleCreateOrdnerLabel}
            />
          </div>
        </div>

        <div class="card-footer">
          <a href="/" class="btn btn-secondary">
            <ArrowLeft size={18} />
            Abbrechen
          </a>
          <button type="submit" disabled={saving} class="btn btn-primary">
            {#if saving}
              <span class="spinner"></span>
              Speichern...
            {:else}
              <Save size={18} />
              Speichern
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
</div>

<style>
  .entry-page {
    max-width: 1000px;
    margin: 0 auto;
    padding: var(--space-6) var(--space-4);
  }
  
  .entry-header {
    text-align: center;
    margin-bottom: var(--space-8);
  }
  
  .entry-header h1 {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-2);
  }
  
  .error-banner {
    padding: var(--space-4);
    background: var(--color-error-subtle);
    border: 1px solid var(--color-error);
    border-radius: var(--radius-lg);
    color: var(--color-error);
    margin-bottom: var(--space-6);
  }
  
  .entry-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
  }
  
  .form-card {
    background: var(--color-background-primary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl);
    overflow: hidden;
  }
  
  .card-header {
    display: flex;
    align-items: flex-start;
    gap: var(--space-4);
    padding: var(--space-6);
    background: var(--color-background-secondary);
    border-bottom: 1px solid var(--color-border);
  }
  
  .card-header.ki-header {
    background: linear-gradient(135deg, var(--color-primary-subtle) 0%, var(--color-background-secondary) 100%);
  }
  
  .header-icon {
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
  
  .ki-header .header-icon {
    background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-primary) 100%);
  }
  
  .header-content {
    flex: 1;
  }
  
  .header-content h2 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-bottom: var(--space-1);
  }
  
  .header-description {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }
  
  .card-body {
    padding: var(--space-6);
  }
  
  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-6);
    background: var(--color-background-secondary);
    border-top: 1px solid var(--color-border);
  }
  
  .form-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }
  
  .form-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-4);
  }
  
  .form-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .form-field.full-width {
    grid-column: 1 / -1;
  }
  
  .field-label {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-secondary);
  }
  
  .field-label .required {
    color: var(--color-error);
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
  
  .field-input::placeholder {
    color: var(--color-text-tertiary);
  }
  
  .field-textarea {
    resize: vertical;
    min-height: 80px;
  }
  
  .field-textarea.field-monospace {
    font-family: 'SF Mono', Monaco, monospace;
    font-size: var(--font-size-sm);
  }
  
  .field-select {
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 40px;
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
  }
  
  .btn-primary {
    background: var(--color-primary);
    color: white;
    border: none;
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
  
  @media (max-width: 768px) {
    .entry-page {
      padding: var(--space-4);
    }
    
    .entry-header h1 {
      font-size: var(--font-size-2xl);
    }
    
    .form-row {
      grid-template-columns: 1fr;
    }
    
    .card-header {
      flex-direction: column;
      gap: var(--space-3);
    }
    
    .card-footer {
      flex-direction: column-reverse;
      gap: var(--space-3);
    }
    
    .btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>
