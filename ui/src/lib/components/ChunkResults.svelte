<script lang="ts">
	import { ChevronLeft, ChevronRight, FileText, AlertCircle, ExternalLink } from 'lucide-svelte';
	import { apiClient } from '$lib/api.js';
	import type { ChunkResultItem } from '$lib/api.js';
	import type { ChunkQuery } from '$lib/chunkSearch.js';
	import { highlightTerms } from '$lib/highlight.js';

	interface Props {
		query: ChunkQuery;
		onPageChange: (page: number) => void;
	}

	let { query, onPageChange }: Props = $props();

	const opening = $state<Record<number, boolean>>({});

	async function openOriginal(id: number, page: number | null) {
		if (opening[id]) return;
		opening[id] = true;
		try {
			// Auth via the apiClient interceptor (JWT from localStorage); fetch as a blob so the
			// browser can open the PDF inline in a new tab without leaking the token into a URL.
			const resp = await apiClient.get(`/files/chunks/${id}/view`, { responseType: 'blob' });
			const url = URL.createObjectURL(resp.data);
			// page is the 1-indexed physical PDF page (PyMuPDF page_num+1); the #page=N fragment
			// makes the browser's PDF viewer jump straight to it.
			window.open(page ? `${url}#page=${page}` : url, '_blank');
			setTimeout(() => URL.revokeObjectURL(url), 60_000);
		} catch (e) {
			alert('Fehler beim Öffnen der Originaldatei: ' + (e instanceof Error ? e.message : String(e)));
		} finally {
			opening[id] = false;
		}
	}

	function highlight(text: string, q: string): string {
		return highlightTerms(text, q, 'chunk-highlight');
	}

	function snippet(text: string, q: string, max = 220): string {
		let idx = 0;
		const terms = q.trim().split(/\s+/).filter((t) => t.length > 2);
		if (terms.length) {
			const hit = terms.find((t) => text.toLowerCase().includes(t.toLowerCase()));
			if (hit) idx = Math.max(0, text.toLowerCase().indexOf(hit.toLowerCase()) - 60);
		}
		const start = Math.max(0, idx);
		const end = Math.min(text.length, start + max);
		const prefix = start > 0 ? '…' : '';
		const suffix = end < text.length ? '…' : '';
		return prefix + highlight(text.slice(start, end), q) + suffix;
	}

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}

	function pages(current: number, total: number): (number | string)[] {
		if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
		if (current <= 3) return [1, 2, 3, 4, '…', total];
		if (current >= total - 2) return [1, '…', total - 3, total - 2, total - 1, total];
		return [1, '…', current - 1, current, current + 1, '…', total];
	}
</script>

<div class="chunk-results">
	{#if query.error}
		<div class="error-banner">
			<AlertCircle size={16} />
			<span>{query.error}</span>
		</div>
	{:else if query.isLoading}
		<div class="loading">
			<span>Leitlinien durchsuchen…</span>
		</div>
	{:else if query.results.length === 0}
		{#if query.query}
			<div class="empty">Keine Treffer gefunden.</div>
		{/if}
	{:else}
		<div class="result-count">{query.total} Treffer</div>
		<ul class="chunk-list">
			{#each query.results as item (item.id)}
				<li class="chunk-item">
					<div class="chunk-header">
						<span class="chunk-icon"><FileText size={16} /></span>
						<span class="awmf-badge">{item.awmf ?? '—'}</span>
						<span class="chunk-title">{item.title}</span>
						<span class="chunk-source-chip">{item.society ?? ''}</span>
						{#if item.page != null}
							<span class="chunk-page">Seite {item.page}</span>
						{/if}
						<span class="chunk-score" title="Relevanz">{formatScore(item.score)}</span>
						<button
							class="open-btn"
							onclick={() => openOriginal(item.id, item.page)}
							disabled={opening[item.id]}
						>
							<ExternalLink size={13} />
							{opening[item.id] ? 'Lädt…' : 'Original öffnen'}
						</button>
					</div>
					<p class="chunk-text">{@html snippet(item.text, query.query)}</p>
				</li>
			{/each}
		</ul>

		{#if query.totalPages > 1}
			<nav class="pagination">
				<button
					class="page-btn"
					disabled={query.page <= 1}
					onclick={() => onPageChange(query.page - 1)}
					aria-label="Vorherige Seite"
				>
					<ChevronLeft size={16} />
				</button>
				{#each pages(query.page, query.totalPages) as p, i}
					{#if p === '…'}
						<span class="page-ellipsis">…</span>
					{:else}
						<button
							class="page-btn"
							class:active={query.page === p}
							onclick={() => onPageChange(p as number)}
						>
							{p}
						</button>
					{/if}
				{/each}
				<button
					class="page-btn"
					disabled={query.page >= query.totalPages}
					onclick={() => onPageChange(query.page + 1)}
					aria-label="Nächste Seite"
				>
					<ChevronRight size={16} />
				</button>
			</nav>
		{/if}
	{/if}
</div>

<style>
	.chunk-results {
		padding: 0;
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
	.loading {
		padding: 2rem;
		text-align: center;
		color: #6b7280;
	}
	.empty {
		padding: 2rem;
		text-align: center;
		color: #6b7280;
	}
	.result-count {
		color: #6b7280;
		font-size: 0.85rem;
		margin: 0 0 0.75rem;
	}
	.chunk-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.chunk-item {
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		padding: 0.9rem 1rem;
		background: var(--color-background-primary);
		max-width: 100%;
		overflow-wrap: anywhere;
	}
	.chunk-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.5rem;
	}
	.chunk-icon {
		color: #059669;
		flex-shrink: 0;
	}
	.awmf-badge {
		background: #ecfdf5;
		color: #047857;
		border: 1px solid #a7f3d0;
		border-radius: 6px;
		padding: 0.1rem 0.45rem;
		font-size: 0.75rem;
		font-weight: 600;
	}
	.chunk-title {
		font-weight: 600;
		color: #111827;
		min-width: 0;
		flex: 1 1 auto;
		overflow-wrap: anywhere;
	}
	.chunk-source-chip {
		background: #f3f4f6;
		color: #374151;
		border-radius: 6px;
		padding: 0.1rem 0.45rem;
		font-size: 0.75rem;
		max-width: 100%;
		overflow-wrap: anywhere;
	}
	.chunk-page {
		color: #6b7280;
		font-size: 0.8rem;
	}
	.chunk-score {
		margin-left: auto;
		color: #4b5563;
		font-size: 0.8rem;
		font-weight: 600;
	}
	.open-btn {
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
	.open-btn:disabled {
		opacity: 0.6;
		cursor: default;
	}
	.open-btn:hover:not(:disabled) {
		background: #ecfdf5;
	}
	.chunk-text {
		margin: 0;
		color: #374151;
		font-size: 0.9rem;
		line-height: 1.45;
		overflow-wrap: anywhere;
		word-break: break-word;
	}
	:global(.chunk-highlight) {
		background: #fef08a;
		border-radius: 2px;
		padding: 0 1px;
	}
	.pagination {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		flex-wrap: wrap;
		justify-content: center;
		margin-top: 1.25rem;
	}
	.page-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2rem;
		height: 2rem;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		background: var(--color-background-primary);
		color: #374151;
		cursor: pointer;
	}
	.page-btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.page-btn.active {
		background: #059669;
		color: #fff;
		border-color: #059669;
	}
	.page-ellipsis {
		color: #9ca3af;
		padding: 0 0.25rem;
	}
</style>
