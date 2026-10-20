<script lang="ts">
	import { ArrowLeft, Save, FolderOpen, X } from 'lucide-svelte';
	import type { PageData } from './$types';
	import { entriesApi, classificationsApi } from '$lib/api';
	import type { EntryTagSuggestionsResponse } from '$lib/api';
	import MultiSelect from '$lib/components/MultiSelect.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	function formSnapshot(d: PageData) {
		const e = d.entry;
		return {
			titel: e.titel,
			zusammenfassung: e.zusammenfassung || '',
			inhalt: e.inhalt,
			quelle: e.quelle || '',
			dokumenttypId: e.dokumenttyp_id ?? null,
			schwierigkeit: e.schwierigkeit || '',
			selectedFachgebiete: e.fachgebiete.map((f: { id: number }) => f.id),
			selectedDiagnosen: e.diagnosen.map((d: { id: number }) => d.id),
			selectedSymptome: e.symptome.map((s: { id: number }) => s.id),
			selectedOrdnerLabels: e.ordner_labels.map((l: { id: number }) => l.id),
			dokumenttypen: d.dokumenttypen,
			ordnerLabels: d.ordnerLabels,
			fachOptions: d.fachgebiete,
			diagnosenOptions: d.diagnosen,
			symptomeOptions: d.symptome,
			tagSuggestions: d.tagSuggestions
		};
	}

	let { data }: { data: PageData } = $props();
	// Initial form snapshot — plain const (not reactive) so each field below
	// initializes from it without `state_referenced_locally` noise. The effect
	// further down re-snapshots on same-route entry changes.
	const initial = formSnapshot(data);

	let titel = $state(initial.titel);
	let zusammenfassung = $state(initial.zusammenfassung);
	let inhalt = $state(initial.inhalt);
	let quelle = $state(initial.quelle);
	let dokumenttypId: number | null = $state(initial.dokumenttypId);
	let schwierigkeit = $state(initial.schwierigkeit);

	let selectedFachgebiete = $state(initial.selectedFachgebiete);
	let selectedDiagnosen = $state(initial.selectedDiagnosen);
	let selectedSymptome = $state(initial.selectedSymptome);
	let selectedOrdnerLabels = $state(initial.selectedOrdnerLabels);

	// Local option lists (mutable for inline-create)
	let dokumenttypen = $state<{ id: number; name: string }[]>(initial.dokumenttypen);
	let ordnerLabels = $state<{ id: number; name: string }[]>(initial.ordnerLabels);
	let fachOptions = $state<{ id: number; name: string }[]>(initial.fachOptions);
	let diagnosenOptions = $state<{ id: number; code: string; name: string }[]>(initial.diagnosenOptions);
	let symptomeOptions = $state<{ id: number; name: string }[]>(initial.symptomeOptions);

	let tagSuggestions = $state<EntryTagSuggestionsResponse | null>(initial.tagSuggestions);
	let suggestionsDismissed = $state(false);
	let applyingSuggestions = $state(false);

	// SvelteKit does not remount on same-route param change (/entry/3/edit →
	// /entry/7/edit): re-snapshot all form state from the new load data.
	let lastEntryId: number | null = null;
	$effect(() => {
		const e = data.entry;
		if (lastEntryId === e.id) return;
		lastEntryId = e.id;
		const s = formSnapshot(data);
		titel = s.titel;
		zusammenfassung = s.zusammenfassung;
		inhalt = s.inhalt;
		quelle = s.quelle;
		dokumenttypId = s.dokumenttypId;
		schwierigkeit = s.schwierigkeit;
		selectedFachgebiete = s.selectedFachgebiete;
		selectedDiagnosen = s.selectedDiagnosen;
		selectedSymptome = s.selectedSymptome;
		selectedOrdnerLabels = s.selectedOrdnerLabels;
		dokumenttypen = s.dokumenttypen;
		ordnerLabels = s.ordnerLabels;
		fachOptions = s.fachOptions;
		diagnosenOptions = s.diagnosenOptions;
		symptomeOptions = s.symptomeOptions;
		tagSuggestions = s.tagSuggestions;
		suggestionsDismissed = false;
	});

	let saving = $state(false);
	let error = $state<string | null>(null);

	const hasTagSuggestions = $derived(
		(tagSuggestions?.has_actionable_suggestions ?? false) && !suggestionsDismissed
	);

	function applyCuratedSuggestions() {
		for (const suggestion of tagSuggestions?.fachgebiete ?? []) {
			if (suggestion.id !== null && !suggestion.already_linked && !selectedFachgebiete.includes(suggestion.id)) {
				selectedFachgebiete = [...selectedFachgebiete, suggestion.id];
			}
		}
	}

	async function ensureDokumenttyp(name: string): Promise<number | null> {
		const trimmed = name.trim();
		if (!trimmed) return null;
		const existing = dokumenttypen.find((t) => t.name.toLowerCase() === trimmed.toLowerCase());
		if (existing) return existing.id;
		try {
			const created = await classificationsApi.createDokumenttyp({ name: trimmed });
			dokumenttypen = [...dokumenttypen, created];
			return created.id;
		} catch {
			// 409 = already exists → resolve to its ID
			dokumenttypen = await classificationsApi.getDokumenttypen();
			return dokumenttypen.find((t) => t.name.toLowerCase() === trimmed.toLowerCase())?.id ?? null;
		}
	}

	async function ensureOrdnerLabel(name: string): Promise<number | null> {
		const trimmed = name.trim();
		if (!trimmed) return null;
		const existing = ordnerLabels.find((l) => l.name.toLowerCase() === trimmed.toLowerCase());
		if (existing) return existing.id;
		try {
			const created = await classificationsApi.createOrdnerLabel({ name: trimmed });
			ordnerLabels = [...ordnerLabels, created];
			return created.id;
		} catch {
			// 409 = already exists → resolve to its ID
			ordnerLabels = await classificationsApi.getOrdnerLabels();
			return ordnerLabels.find((l) => l.name.toLowerCase() === trimmed.toLowerCase())?.id ?? null;
		}
	}

	async function handleCreateFachgebiet(detail: { value: string }) {
		const name = detail.value.trim();
		if (!name) return;
		try {
			const created = await classificationsApi.createFachgebiet({ name });
			fachOptions = [...fachOptions, created];
			selectedFachgebiete = [...selectedFachgebiete, created.id];
		} catch {
			// 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates
			const resolved = await classificationsApi.resolveLabels({
				fachgebiete: [name],
				diagnosen: [],
				symptome: []
			});
			if (resolved.fachgebiet_ids.length > 0) {
				fachOptions = await classificationsApi.getFachgebiete();
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
				diagnosenOptions = await classificationsApi.getDiagnosen();
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
			symptomeOptions = [...symptomeOptions, created];
			selectedSymptome = [...selectedSymptome, created.id];
		} catch {
			// 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates
			const resolved = await classificationsApi.resolveLabels({ symptome: [name] });
			if (resolved.symptom_ids.length > 0) {
				symptomeOptions = await classificationsApi.getSymptome();
				selectedSymptome = [...selectedSymptome, resolved.symptom_ids[0]];
			}
		}
	}

	async function handleCreateOrdnerLabel(detail: { value: string }) {
		const id = await ensureOrdnerLabel(detail.value);
		if (id !== null && !selectedOrdnerLabels.includes(id)) {
			selectedOrdnerLabels = [...selectedOrdnerLabels, id];
		}
	}

	async function applyFolderSuggestions() {
		if (!tagSuggestions || applyingSuggestions) return;
		try {
			applyingSuggestions = true;
			error = null;
			tagSuggestions = await entriesApi.applyTagSuggestions(data.entry.id);
			if (tagSuggestions.dokumenttyp) {
				const id = await ensureDokumenttyp(tagSuggestions.dokumenttyp);
				if (id !== null) dokumenttypId = id;
			}
			for (const label of tagSuggestions.stored_hierarchy ?? []) {
				const id = await ensureOrdnerLabel(label);
				if (id !== null && !selectedOrdnerLabels.includes(id)) {
					selectedOrdnerLabels = [...selectedOrdnerLabels, id];
				}
			}
			applyCuratedSuggestions();
		} catch (err) {
			console.error('Failed to apply folder suggestions:', err);
			error = 'Fehler beim Übernehmen der Ordner-Labels';
		} finally {
			applyingSuggestions = false;
		}
	}


	onMount(() => {
		if (tagSuggestions?.has_actionable_suggestions) applyCuratedSuggestions();
	});
	
	async function handleSubmit(e: Event) {
		e.preventDefault();
		
		if (!titel.trim() || !inhalt.trim()) {
			error = 'Titel und Inhalt sind erforderlich';
			return;
		}
		
		try {
			saving = true;
			error = null;
			
			await entriesApi.update(data.entry.id, {
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
			});
			
			goto(`/entry/${data.entry.id}`);
		} catch (err) {
			console.error('Failed to update entry:', err);
			error = 'Fehler beim Speichern des Eintrags';
		} finally {
			saving = false;
		}
	}
	
</script>

<svelte:head>
	<title>{titel} bearbeiten | MedWiss DB</title>
</svelte:head>

<div class="edit-page">
	<header class="edit-header">
		<a href="/entry/{data.entry.id}" class="back-link">
			<ArrowLeft size={20} />
			Zurück zum Eintrag
		</a>
	</header>
	
	<div class="edit-container">
		<h1 class="edit-title">Eintrag bearbeiten</h1>
		
		{#if error}
			<div class="error-banner">{error}</div>
		{/if}

		{#if hasTagSuggestions}
			<div class="suggestions-banner">
				<div class="suggestions-content">
					<FolderOpen size={18} />
					<div>
						<p class="suggestions-title">Vorschläge aus Ordnerstruktur</p>
						{#if (tagSuggestions?.missing_hierarchy?.length ?? 0) > 0}
							<p class="suggestions-labels">
								{#each tagSuggestions?.missing_hierarchy ?? [] as label, i}
									<span class="suggestion-chip">{label}</span>{#if i < (tagSuggestions?.missing_hierarchy.length ?? 0) - 1}, {/if}
								{/each}
							</p>
						{/if}
						{#if tagSuggestions?.dokumenttyp && tagSuggestions.dokumenttyp !== tagSuggestions.stored_dokumenttyp}
							<p class="suggestions-meta">Dokumenttyp: {tagSuggestions.dokumenttyp}</p>
						{/if}
						{#if tagSuggestions?.unterkategorie}
							<p class="suggestions-meta">Unterkategorie: {tagSuggestions.unterkategorie}</p>
						{/if}
					</div>
				</div>
				<div class="suggestions-actions">
					<button
						type="button"
						class="suggestions-apply-btn"
						disabled={applyingSuggestions}
						onclick={applyFolderSuggestions}
					>
						{applyingSuggestions ? 'Wird übernommen…' : 'Ordner-Labels übernehmen'}
					</button>
					<button
						type="button"
						class="suggestions-dismiss-btn"
						aria-label="Vorschläge ausblenden"
						onclick={() => (suggestionsDismissed = true)}
					>
						<X size={16} />
					</button>
				</div>
			</div>
		{/if}
		
		<form onsubmit={handleSubmit} class="edit-form">
			<div class="form-section">
				<label class="form-label">
					<span class="label-text">Titel *</span>
					<input type="text" bind:value={titel} required class="form-input" />
				</label>
				
			<label class="form-label">
				<span class="label-text">
					Zusammenfassung
				</span>
			<textarea bind:value={zusammenfassung} rows={3} class="form-textarea"></textarea>
			</label>
				
				<label class="form-label">
					<span class="label-text">Inhalt *</span>
					<textarea bind:value={inhalt} rows={15} required class="form-textarea content-textarea"></textarea>
				</label>
				
				<label class="form-label">
					<span class="label-text">Quelle</span>
					<input type="text" bind:value={quelle} class="form-input" />
				</label>
			</div>
			
			<div class="form-section">
				<h3 class="section-title">Tags</h3>
				<div class="form-row">
					<label class="form-label">
						<span class="label-text">Schwierigkeit</span>
						<select bind:value={schwierigkeit} class="form-select">
							<option value="">-- Auswählen --</option>
							<option value="anfaenger">Anfänger</option>
							<option value="fortgeschritten">Fortgeschritten</option>
							<option value="experte">Experte</option>
						</select>
					</label>

					<label class="form-label">
						<span class="label-text">Dokumenttyp</span>
						<select bind:value={dokumenttypId} class="form-select">
							<option value={null}>-- Auswählen --</option>
							{#each dokumenttypen as typ (typ.id)}
								<option value={typ.id}>{typ.name}</option>
							{/each}
						</select>
					</label>
				</div>

				<div class="multiselect-stack">
					<MultiSelect
						label="Ordner-Labels"
						options={ordnerLabels.map((l) => ({ id: l.id, label: l.name }))}
						bind:selected={selectedOrdnerLabels}
						allowCreate={true}
						createLabel="+ Neues Ordner-Label"
						oncreate={handleCreateOrdnerLabel}
					/>
					<MultiSelect
						label="Fachgebiete"
						options={fachOptions.map((f) => ({ id: f.id, label: f.name }))}
						bind:selected={selectedFachgebiete}
						allowCreate={true}
						createLabel="+ Neues Fachgebiet"
						oncreate={handleCreateFachgebiet}
					/>
					<MultiSelect
						label="Diagnosen"
						options={diagnosenOptions.map((d) => ({ id: d.id, label: d.code ? `${d.code}: ${d.name}` : d.name }))}
						bind:selected={selectedDiagnosen}
						allowCreate={true}
						createLabel="+ Neue Diagnose"
						oncreate={handleCreateDiagnose}
					/>
					<MultiSelect
						label="Symptome"
						options={symptomeOptions.map((s) => ({ id: s.id, label: s.name }))}
						bind:selected={selectedSymptome}
						allowCreate={true}
						createLabel="+ Neues Symptom"
						oncreate={handleCreateSymptom}
					/>
				</div>
			</div>
			
			<div class="form-actions">
				<a href="/entry/{data.entry.id}" class="cancel-button">Abbrechen</a>
				<button type="submit" class="save-button" disabled={saving}>
					<Save size={18} />
					{saving ? 'Speichern...' : 'Speichern'}
				</button>
			</div>
		</form>
	</div>
</div>

<style>
	.edit-page {
		max-width: 1000px;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
	}
	
	.edit-header {
		margin-bottom: var(--space-6);
	}
	
	.back-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-text-secondary);
		text-decoration: none;
		font-size: var(--font-size-sm);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}
	
	.back-link:hover {
		color: var(--color-primary);
		background: var(--color-background-secondary);
	}
	
	.edit-container {
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-xl);
		padding: var(--space-8);
	}
	
	.edit-title {
		font-size: var(--font-size-2xl);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-6);
	}
	
	.error-banner {
		background: var(--color-error-subtle);
		color: var(--color-error);
		padding: var(--space-4);
		border-radius: var(--radius-lg);
		margin-bottom: var(--space-6);
	}
	
	.suggestions-banner {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4);
		background: #eff6ff;
		color: #1d4ed8;
		padding: var(--space-4);
		border-radius: var(--radius-lg);
		margin-bottom: var(--space-6);
		border: 1px solid #bfdbfe;
		font-size: var(--font-size-sm);
	}

	.suggestions-content {
		display: flex;
		gap: var(--space-3);
	}

	.suggestions-title {
		font-weight: var(--font-weight-semibold);
		margin-bottom: var(--space-1);
	}

	.suggestions-labels {
		margin: 0;
	}

	.suggestions-meta {
		margin: var(--space-2) 0 0;
		font-size: var(--font-size-xs);
		opacity: 0.9;
	}

	.suggestions-actions {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-shrink: 0;
	}

	.suggestions-apply-btn {
		padding: var(--space-2) var(--space-3);
		border: 1px solid #93c5fd;
		border-radius: var(--radius-md);
		background: white;
		color: #1d4ed8;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
	}

	.suggestions-apply-btn:hover:not(:disabled) {
		background: #dbeafe;
	}

	.suggestions-dismiss-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-2);
		border: none;
		border-radius: var(--radius-md);
		background: transparent;
		color: #1d4ed8;
		cursor: pointer;
	}

	.suggestions-dismiss-btn:hover {
		background: #dbeafe;
	}

	.form-section {
		margin-bottom: var(--space-6);
		padding-bottom: var(--space-6);
		border-bottom: 1px solid var(--color-border);
	}
	
	.form-section:last-of-type {
		border-bottom: none;
	}
	
	.section-title {
		font-size: var(--font-size-base);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-3);
	}
	
	.form-label {
		display: block;
		margin-bottom: var(--space-4);
	}
	
	.label-text {
		display: block;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-secondary);
		margin-bottom: var(--space-2);
	}
	
	.form-input,
	.form-textarea,
	.form-select {
		width: 100%;
		padding: var(--space-3);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		background: var(--color-background-primary);
		color: var(--color-text-primary);
		transition: border-color var(--transition-fast);
	}
	
	.form-input:focus,
	.form-textarea:focus,
	.form-select:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: var(--shadow-focus);
	}
	
	.form-textarea {
		resize: vertical;
		font-family: inherit;
	}
	
	.content-textarea {
		min-height: 300px;
		white-space: pre-wrap;
	}
	
	.form-row {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: var(--space-4);
	}


	.multiselect-stack {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	
	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-4);
		padding-top: var(--space-6);
		border-top: 1px solid var(--color-border);
	}
	
	.cancel-button {
		padding: var(--space-3) var(--space-6);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		color: var(--color-text-secondary);
		text-decoration: none;
		font-weight: var(--font-weight-medium);
		transition: all var(--transition-fast);
	}
	
	.cancel-button:hover {
		border-color: var(--color-text-secondary);
		color: var(--color-text-primary);
	}
	
	.save-button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius-lg);
		font-weight: var(--font-weight-semibold);
		cursor: pointer;
		transition: all var(--transition-fast);
	}
	
	.save-button:hover:not(:disabled) {
		background: var(--color-primary-dark);
	}
	
	.save-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
	
	@media (max-width: 768px) {
		.edit-container {
			padding: var(--space-5);
		}
		
		.form-row {
			grid-template-columns: 1fr;
		}
	}
</style>
