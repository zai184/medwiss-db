<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Search, X, History as HistoryIcon, Sparkles } from 'lucide-svelte';
	import ChunkResults from '$lib/components/ChunkResults.svelte';
	import RagResults from '$lib/components/RagResults.svelte';
	import {
		initialChunkQuery,
		searchChunks,
		answerRag,
		initialRagQuery,
		loadHistory,
		pushHistory,
		clearHistory,
	} from '$lib/chunkSearch.js';

	// Env-driven gate: page disabled on the VPS build (VITE_DISABLE_LEITLINIEN=1).
	const leitlinienDisabled = import.meta.env.VITE_DISABLE_LEITLINIEN === '1';
	onMount(() => {
		if (leitlinienDisabled) goto('/', { replaceState: true });
	});
	type Mode = 'suche' | 'antwort';

	let query = $state(initialChunkQuery());
	let rag = $state(initialRagQuery());
	let mode = $state<Mode>('suche');
	let history = $state<string[]>([]);
	let showHistory = $state(false);
	let inputEl: HTMLInputElement;

	onMount(() => {
		history = loadHistory();
	});

	async function runSearch(qOverride?: string) {
		const q = (qOverride ?? query.query).trim();
		if (!q) return;
		if (mode === 'antwort') {
			rag = await answerRag({ ...rag, query: q });
		} else {
			query = await searchChunks({ ...query, query: q, page: 1 });
		}
		history = pushHistory(q);
		showHistory = false;
	}

	async function goToPage(page: number) {
		if (page < 1 || page > query.totalPages) return;
		query = await searchChunks({ ...query, page });
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter') runSearch();
	}

	function clearInput() {
		query = { ...query, query: '' };
		rag = { ...rag, query: '', answer: '', sources: [] };
		inputEl?.focus();
	}

	function clearHist() {
		clearHistory();
		history = [];
	}
</script>

<svelte:head>
	<title>Leitlinien-Suche | MedWiss DB</title>
</svelte:head>

<div class="leitlinien-page">
	<header class="leitlinien-header">
		<h1>Leitlinien-Suche</h1>
	</header>

	<div class="leitlinien-container">
		<div class="search-input-wrapper">
			<div class="search-input-container">
				<span class="search-icon"><Search size={20} /></span>
				<input
					bind:this={inputEl}
					type="text"
					class="search-input"
					bind:value={query.query}
					onkeydown={handleKeyDown}
					onfocus={() => (showHistory = history.length > 0)}
				/>
				{#if query.query}
					<button class="clear-input-btn" onclick={clearInput} aria-label="Eingabe löschen">
						<X size={18} />
					</button>
				{/if}
				<button class="search-btn" onclick={() => runSearch()}>
					<span>{mode === 'antwort' ? 'Antworten' : 'Suchen'}</span>
				</button>
			</div>

			<div class="mode-toggle">
				<button
					class="mode-btn"
					class:active={mode === 'suche'}
					onclick={() => (mode = 'suche')}
				>
					Passagen
				</button>
				<button
					class="mode-btn"
					class:active={mode === 'antwort'}
					onclick={() => (mode = 'antwort')}
				>
					<Sparkles size={13} />
					Antwort
				</button>
			</div>

			{#if showHistory && history.length > 0}
				<div class="history-dropdown">
					<div class="history-header">
						<div class="history-title">
							<HistoryIcon size={16} />
							<span>Letzte Suchen</span>
						</div>
						<button class="clear-history-btn" onclick={clearHist}>Alle löschen</button>
					</div>
					<div class="history-list">
						{#each history as item}
							<div
								class="history-item"
								role="button"
								tabindex="0"
								onclick={() => {
									query.query = item;
									runSearch(item);
								}}
								onkeydown={(e) => e.key === 'Enter' && (query.query = item) && runSearch(item)}
							>
								<span class="history-query">{item}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<div class="results-area">
			{#if mode === 'antwort'}
				<RagResults {rag} />
			{:else}
				<ChunkResults {query} onPageChange={goToPage} />
			{/if}
		</div>
	</div>
</div>

<svelte:window
	onclick={(e) => {
		if (showHistory && !(e.target as Element)?.closest('.search-input-wrapper')) {
			showHistory = false;
		}
	}}
/>

<style>
	.leitlinien-page {
		max-width: 1000px;
		margin: 0 auto;
		padding: 1.5rem 2rem;
	}
	.leitlinien-header h1 {
		margin: 0 0 0.25rem;
		font-size: 1.5rem;
		color: #111827;
	}
	.leitlinien-container {
		position: relative;
	}
	.search-input-wrapper {
		position: relative;
		max-width: 720px;
		margin-bottom: 1.5rem;
	}
	.search-input-container {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 0 0.75rem;
		background: var(--color-background-primary);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
	}
	.search-icon {
		color: #6b7280;
		flex-shrink: 0;
	}
	.search-input {
		flex: 1;
		border: none;
		outline: none;
		padding: 0.8rem 0;
		font-size: 1rem;
		background: transparent;
	}
	.clear-input-btn {
		display: inline-flex;
		align-items: center;
		border: none;
		background: none;
		color: #9ca3af;
		cursor: pointer;
		padding: 0.25rem;
	}
	.search-btn {
		background: #059669;
		color: #fff;
		border: none;
		border-radius: 8px;
		padding: 0.55rem 1.2rem;
		font-weight: 600;
		cursor: pointer;
	}
	.mode-toggle {
		display: inline-flex;
		gap: 0.25rem;
		margin-top: 0.6rem;
		background: #f3f4f6;
		border-radius: 8px;
		padding: 0.2rem;
	}
	.mode-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		border: none;
		background: transparent;
		border-radius: 6px;
		padding: 0.3rem 0.8rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: #6b7280;
		cursor: pointer;
	}
	.mode-btn.active {
		background: var(--color-background-primary);
		color: #059669;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
	}
	.history-dropdown {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		background: var(--color-background-primary);
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
		z-index: 50;
		overflow: hidden;
	}
	.history-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.6rem 0.9rem;
		border-bottom: 1px solid #f3f4f6;
	}
	.history-title {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		color: #6b7280;
		font-size: 0.85rem;
	}
	.clear-history-btn {
		border: none;
		background: none;
		color: #059669;
		cursor: pointer;
		font-size: 0.8rem;
	}
	.history-list {
		max-height: 240px;
		overflow-y: auto;
	}
	.history-item {
		display: flex;
		align-items: center;
		padding: 0.6rem 0.9rem;
		cursor: pointer;
		font-size: 0.9rem;
	}
	.history-item:hover {
		background: #f9fafb;
	}
	.history-query {
		color: #374151;
	}
	.results-area {
		max-width: 900px;
	}
</style>
