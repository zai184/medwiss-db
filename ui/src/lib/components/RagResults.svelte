<script lang="ts">
	import { FileText, ExternalLink, AlertCircle } from 'lucide-svelte';
	import { apiClient } from '$lib/api.js';
	import { marked } from 'marked';
	import DOMPurify from 'isomorphic-dompurify';
	import type { RagQuery } from '$lib/chunkSearch.js';

	interface Props {
		rag: RagQuery;
	}

	let { rag }: Props = $props();

	const opening = $state<Record<number, boolean>>({});

	// LLM output is untrusted: parse markdown, then strip any HTML/script via DOMPurify
	// before injecting. Prevents XSS from a crafted or accidentally-hallucinated answer.
	let renderedAnswer = $derived(rag.answer ? DOMPurify.sanitize(marked.parse(rag.answer) as string) : '');

	async function openSource(id: number, page: number | null) {
		if (opening[id]) return;
		opening[id] = true;
		try {
			const resp = await apiClient.get(`/files/chunks/${id}/view`, { responseType: 'blob' });
			const url = URL.createObjectURL(resp.data);
			window.open(page ? `${url}#page=${page}` : url, '_blank');
			setTimeout(() => URL.revokeObjectURL(url), 60_000);
		} catch (e) {
			alert('Fehler beim Öffnen der Originaldatei: ' + (e instanceof Error ? e.message : String(e)));
		} finally {
			opening[id] = false;
		}
	}

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}
</script>

<div class="rag-results">
	{#if rag.error}
		<div class="error-banner">
			<AlertCircle size={16} />
			<span>{rag.error}</span>
		</div>
	{:else if rag.isLoading}
		<div class="loading">
			<span>Leitlinien auswerten (ca. 30 s)…</span>
		</div>
	{:else if rag.answer}
		<div class="rag-answer">
			<h2>Antwort</h2>
			<div class="answer-text">{@html renderedAnswer}</div>
		</div>

		<div class="rag-sources">
			<h2>Quellen ({rag.sources.length})</h2>
			<ul class="source-list">
				{#each rag.sources as src (src.id)}
					<li class="source-item">
						<span class="source-icon"><FileText size={15} /></span>
						<span class="source-awmf">{src.awmf ?? '—'}</span>
						<span class="source-title">{src.title}</span>
						{#if src.page != null}
							<span class="source-page">Seite {src.page}</span>
						{/if}
						<span class="source-score" title="Relevanz">{formatScore(src.score)}</span>
						<button
							class="source-open-btn"
							onclick={() => openSource(src.id, src.page)}
							disabled={opening[src.id]}
						>
							<ExternalLink size={13} />
							{opening[src.id] ? 'Lädt…' : 'Original öffnen'}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{:else if !rag.query}
		<div class="empty">Geben Sie eine Frage ein und wählen Sie „Antwort“.</div>
	{/if}
</div>

<style>
	.rag-results {
		max-width: 900px;
	}
	.error-banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		background: #fef2f2;
		color: #b91c1c;
		border: 1px solid #fecaca;
		border-radius: 8px;
		padding: 0.75rem 1rem;
	}
	.loading,
	.empty {
		padding: 2rem;
		text-align: center;
		color: #6b7280;
	}
	.rag-answer {
		background: var(--color-background-primary);
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		padding: 1.25rem 1.5rem;
		margin-bottom: 1.25rem;
	}
	.rag-answer h2,
	.rag-sources h2 {
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #6b7280;
		margin: 0 0 0.75rem;
	}
	.answer-text {
		color: #111827;
		font-size: 0.95rem;
		line-height: 1.55;
	}
	.answer-text :global(p) {
		margin: 0 0 0.6rem;
	}
	.answer-text :global(p:last-child) {
		margin-bottom: 0;
	}
	.answer-text :global(ul),
	.answer-text :global(ol) {
		margin: 0 0 0.6rem;
		padding-left: 1.4rem;
	}
	.answer-text :global(li) {
		margin-bottom: 0.25rem;
	}
	.answer-text :global(strong) {
		font-weight: 600;
	}
	.answer-text :global(h1),
	.answer-text :global(h2),
	.answer-text :global(h3) {
		margin: 0.75rem 0 0.4rem;
		font-size: 1.05rem;
	}
	.answer-text :global(code) {
		background: #f3f4f6;
		border-radius: 4px;
		padding: 0.1rem 0.3rem;
		font-size: 0.85em;
	}
	.answer-text :global(pre) {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 0.75rem;
		overflow-x: auto;
	}
	.rag-sources h2 {
		margin-bottom: 0.75rem;
	}
	.source-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.source-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 0.6rem 0.8rem;
		background: var(--color-background-primary);
		flex-wrap: wrap;
	}
	.source-icon {
		color: #059669;
		flex-shrink: 0;
	}
	.source-awmf {
		background: #ecfdf5;
		color: #047857;
		border: 1px solid #a7f3d0;
		border-radius: 6px;
		padding: 0.1rem 0.45rem;
		font-size: 0.75rem;
		font-weight: 600;
	}
	.source-title {
		font-weight: 600;
		color: #111827;
		font-size: 0.85rem;
	}
	.source-page {
		color: #6b7280;
		font-size: 0.78rem;
	}
	.source-score {
		margin-left: auto;
		color: #4b5563;
		font-size: 0.78rem;
		font-weight: 600;
	}
	.source-open-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		background: var(--color-background-primary);
		color: #059669;
		border: 1px solid #a7f3d0;
		border-radius: 6px;
		padding: 0.2rem 0.55rem;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}
	.source-open-btn:disabled {
		opacity: 0.6;
		cursor: default;
	}
	.source-open-btn:hover:not(:disabled) {
		background: #ecfdf5;
	}
</style>
