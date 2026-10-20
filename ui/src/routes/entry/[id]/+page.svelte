<script lang="ts">
	import { ArrowLeft, Edit, Calendar, Tag, FileText, User, Save, X } from 'lucide-svelte';
	import FileViewer from '$lib/components/FileViewer.svelte';
	import { entriesApi } from '$lib/api';
	import { marked } from 'marked';
	import DOMPurify from 'isomorphic-dompurify';
	import { renderMermaid } from '$lib/mermaid.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	
	let entry = $derived(data.entry);

	// Inhalt tracks route data; an override holds optimistic inline edits until
	// the next entry (same-route navigation) resets it via the effect below.
	let inhaltOverride = $state<string | null>(null);
	let inhalt = $derived(inhaltOverride ?? entry.inhalt);
	$effect(() => {
		void entry.id;
		inhaltOverride = null;
	});

	// Inline edit state for inhalt (markdown content)
	let editing = $state(false);
	let editInhalt = $state('');
	let savingInhalt = $state(false);
	let saveError = $state<string | null>(null);

	function startEditing() {
		editInhalt = inhalt;
		editing = true;
		saveError = null;
	}

	function cancelEditing() {
		editing = false;
		editInhalt = '';
		saveError = null;
	}

	async function saveInhalt() {
		if (!editInhalt.trim()) {
			saveError = 'Inhalt darf nicht leer sein';
			return;
		}
		try {
			savingInhalt = true;
			saveError = null;
			await entriesApi.update(entry.id, { inhalt: editInhalt });
			inhaltOverride = editInhalt;
			editing = false;
		} catch (err: any) {
			console.error('Failed to save:', err);
			saveError = err?.response?.data?.detail || 'Fehler beim Speichern';
		} finally {
			savingInhalt = false;
		}
	}

	// entry.inhalt is markdown (verified: no pre-existing HTML). Render + sanitize:
	// marked passes any embedded HTML through, DOMPurify strips scripts — safe for
	// imported/AI-generated content.
	let renderedInhalt = $derived(inhalt ? DOMPurify.sanitize(marked.parse(inhalt) as string) : '');

	// ```mermaid fences in the rendered markdown become inline SVGs.
	let markdownEl: HTMLElement | undefined = $state();
	$effect(() => {
		if (renderedInhalt && markdownEl) void renderMermaid(markdownEl);
	});

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('de-DE', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric'
		});
	}
	
	function getDifficultyLabel(diff: string | null): string {
		const diffMap: Record<string, string> = {
			'anfaenger': 'Anfänger',
			'fortgeschritten': 'Fortgeschritten',
			'experte': 'Experte'
		};
		return diff ? diffMap[diff] || diff : '';
	}
</script>

<svelte:head>
	<title>{entry.titel} | MedWiss DB</title>
</svelte:head>

<div class="entry-detail-page">
	<header class="entry-header">
		<button class="back-link" onclick={() => history.back()}>
			<ArrowLeft size={20} />
			<span>Zurück</span>
		</button>
	</header>
	
	<article class="entry-content">
		{#if entry.source_path}
			<FileViewer entryId={entry.id} />
		{/if}
		
		<div class="entry-title-section">
			<h1 class="entry-title">{entry.titel}</h1>
			
			<div class="entry-meta">
				{#if entry.schwierigkeit}
					<span class="difficulty-badge">
						{getDifficultyLabel(entry.schwierigkeit)}
					</span>
				{/if}
				
				{#if entry.unterkategorie}
					<span class="unterkategorie-badge">
						{entry.unterkategorie}
					</span>
				{/if}
				
				<span class="meta-item">
					<Calendar size={14} />
					Erstellt: {formatDate(entry.created_at)}
				</span>
				
				{#if entry.quelle}
					<span class="meta-item">
						<FileText size={14} />
						{entry.quelle}
					</span>
				{/if}
			</div>
		</div>
		
		{#if entry.zusammenfassung}
			<div class="entry-summary">
				<h2 class="section-label">Zusammenfassung</h2>
			<p>{entry.zusammenfassung}</p>
			</div>
		{/if}
		
		<div class="entry-classifications">
			<h2 class="section-label">Tags</h2>
			<div class="tags">
				{#if entry.dokumenttyp_ref || entry.dokumenttyp}
					<span class="tag tag-dokumenttyp">{entry.dokumenttyp_ref?.name ?? entry.dokumenttyp}</span>
				{/if}
				{#each (entry.ordner_labels?.length ? entry.ordner_labels : (entry.source_hierarchy ?? []).map((label: string) => ({ name: label }))) as label}
					<span class="tag tag-hierarchy">{label.name}</span>
				{/each}
				{#each entry.fachgebiete as fach}
					<span class="tag tag-fach">{fach.name}</span>
				{/each}
				{#each entry.diagnosen as diagnose}
					<span class="tag tag-diagnose">
						{diagnose.code ? `${diagnose.code}: ` : ''}{diagnose.name}
					</span>
				{/each}
				{#each entry.symptome as symptom}
					<span class="tag tag-symptom">{symptom.name}</span>
				{/each}
			</div>
		</div>
		
		<div class="entry-body">
			<h2 class="section-label">Inhalt</h2>
			{#if editing}
				<div class="edit-toolbar">
					<button class="toolbar-button save" onclick={saveInhalt} disabled={savingInhalt}>
						<Save size={16} />
						{savingInhalt ? 'Speichert...' : 'Speichern'}
					</button>
					<button class="toolbar-button cancel" onclick={cancelEditing} disabled={savingInhalt}>
						<X size={16} />
						Abbrechen
					</button>
				</div>
				{#if saveError}
					<div class="save-error">{saveError}</div>
				{/if}
				<textarea
					class="content-textarea"
					bind:value={editInhalt}
					rows={20}
					disabled={savingInhalt}
				></textarea>
			{:else}
				<div class="content-body">
					<div class="markdown-content" bind:this={markdownEl}>{@html renderedInhalt}</div>
				</div>
			{/if}
		</div>
		
		<div class="entry-footer">
			{#if !editing}
				<button class="edit-button" onclick={startEditing}>
					<Edit size={18} />
					Bearbeiten
				</button>
			{/if}
		</div>
	</article>
</div>

<style>
	.entry-detail-page {
		max-width: 1400px;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
	}
	
	.entry-header {
		margin-bottom: var(--space-6);
	}
	
	.back-link {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-text-secondary);
		background: none;
		border: none;
		cursor: pointer;
		font-family: inherit;
		font-size: var(--font-size-sm);
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-md);
		transition: all var(--transition-fast);
	}
	
	.back-link:hover {
		color: var(--color-primary);
		background: var(--color-background-secondary);
	}
	
	.entry-content {
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-xl);
		padding: var(--space-8);
	}
	
	.entry-title-section {
		margin-bottom: var(--space-6);
		padding-bottom: var(--space-6);
		border-bottom: 1px solid var(--color-border);
	}
	
	.entry-title {
		font-size: var(--font-size-3xl);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-4);
		line-height: 1.3;
	}
	
	.entry-meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-3);
		align-items: center;
	}
	
	.difficulty-badge {
		padding: 4px 12px;
		border-radius: var(--radius-full);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		background: var(--color-background-tertiary);
		color: var(--color-text-secondary);
	}
	
	.unterkategorie-badge {
		padding: 4px 12px;
		border-radius: var(--radius-full);
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		background: var(--color-primary-subtle);
		color: var(--color-primary-dark);
	}
	
	.meta-item {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: var(--font-size-sm);
		color: var(--color-text-tertiary);
	}
	
	.entry-summary {
		margin-bottom: var(--space-6);
		padding: var(--space-5);
		background: var(--color-background-secondary);
		border-radius: var(--radius-lg);
	}
	
	.entry-summary p {
		color: var(--color-text-secondary);
		line-height: 1.6;
		margin: 0;
	}
	
	.section-label {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--color-text-tertiary);
		margin-bottom: var(--space-3);
	}
	
	.entry-classifications {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-5);
		margin-bottom: var(--space-6);
		padding-bottom: var(--space-6);
		border-bottom: 1px solid var(--color-border);
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	
	.tag {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 6px 12px;
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
	}
	
	.tag-fach {
		background: var(--color-primary-subtle);
		color: var(--color-primary-dark);
	}
	
	.tag-dokumenttyp {
		background: #ede9fe;
		color: #7c3aed;
	}

	.tag-hierarchy {
		background: #f3f4f6;
		color: #4b5563;
	}

	.tag-diagnose {
		background: #d1fae5;
		color: #059669;
	}

	.tag-symptom {
		background: #ffedd5;
		color: #ea580c;
	}
	
	.entry-body {
		margin-bottom: var(--space-6);
	}
	
	.content-body {
		background: var(--color-background-secondary);
		border-radius: var(--radius-lg);
		padding: var(--space-5);
	}
	
	.markdown-content {
		font-family: inherit;
		font-size: var(--font-size-base);
		line-height: 1.7;
		color: var(--color-text-primary);
		white-space: normal;
		word-wrap: break-word;
		margin: 0;
	}
	.markdown-content :global(h1) {
		font-size: 1.4rem;
		margin: 0 0 0.75rem;
	}
	.markdown-content :global(h2) {
		font-size: 1.2rem;
		margin: 1rem 0 0.5rem;
	}
	.markdown-content :global(h3) {
		font-size: 1.05rem;
		margin: 0.9rem 0 0.4rem;
	}
	.markdown-content :global(p) {
		margin: 0 0 0.6rem;
	}
	.markdown-content :global(p:last-child) {
		margin-bottom: 0;
	}
	.markdown-content :global(ul),
	.markdown-content :global(ol) {
		margin: 0 0 0.6rem;
		padding-left: 1.5rem;
	}
	.markdown-content :global(li) {
		margin-bottom: 0.25rem;
	}
	.markdown-content :global(strong) {
		font-weight: 600;
	}
	.markdown-content :global(code) {
		background: var(--color-background);
		border-radius: 4px;
		padding: 0.1rem 0.3rem;
		font-size: 0.85em;
	}
	.markdown-content :global(.mermaid-diagram) {
		margin: 0.75rem 0;
		overflow-x: auto;
		text-align: center;
	}

	.markdown-content :global(.mermaid-diagram svg) {
		max-width: 100%;
		height: auto;
	}

		.markdown-content :global(pre) {
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 0.75rem;
		overflow-x: auto;
		margin: 0 0 0.6rem;
	}

	.edit-toolbar {
		display: flex;
		gap: var(--space-2);
		margin-bottom: var(--space-3);
	}

	.toolbar-button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		border-radius: var(--radius-md);
		font-weight: var(--font-weight-semibold);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
		border: 1px solid var(--color-border);
		background: var(--color-background-primary);
		color: var(--color-text-primary);
	}

	.toolbar-button:hover:not(:disabled) {
		background: var(--color-background-secondary);
	}

	.toolbar-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.toolbar-button.save {
		background: var(--color-primary);
		color: white;
		border-color: var(--color-primary);
	}

	.toolbar-button.save:hover:not(:disabled) {
		background: var(--color-primary-dark);
	}

	.toolbar-button.cancel {
		color: var(--color-text-secondary);
	}

	.content-textarea {
		width: 100%;
		min-height: 400px;
		padding: var(--space-4);
		font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
		font-size: var(--font-size-sm);
		line-height: 1.6;
		color: var(--color-text-primary);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		resize: vertical;
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	.content-textarea:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: var(--shadow-focus);
	}

	.content-textarea:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.save-error {
		margin-bottom: var(--space-3);
		padding: var(--space-3) var(--space-4);
		background: var(--color-error-subtle);
		border: 1px solid var(--color-error);
		border-radius: var(--radius-lg);
		color: var(--color-error);
		font-size: var(--font-size-sm);
	}

	.entry-footer {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
		padding-top: var(--space-6);
		border-top: 1px solid var(--color-border);
	}

	.edit-button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-5);
		background: var(--color-primary);
		color: white;
		text-decoration: none;
		border: none;
		border-radius: var(--radius-lg);
		font-family: inherit;
		font-weight: var(--font-weight-semibold);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: all var(--transition-fast);
	}
	
	.edit-button:hover {
		background: var(--color-primary-dark);
		transform: translateY(-1px);
	}

	@media (max-width: 768px) {
		.entry-detail-page {
			padding: var(--space-4);
		}
		
		.entry-content {
			padding: var(--space-5);
		}
		
		.entry-title {
			font-size: var(--font-size-2xl);
		}
		
		.entry-meta {
			flex-direction: column;
			align-items: flex-start;
		}
		
		.entry-classifications {
			flex-direction: column;
		}
		.entry-content :global(.file-viewer) {
			margin-left: calc(-1 * (var(--space-4) + var(--space-5)));
			margin-right: calc(-1 * (var(--space-4) + var(--space-5)));
			width: calc(100% + 2 * (var(--space-4) + var(--space-5)));
		}
	}
</style>
