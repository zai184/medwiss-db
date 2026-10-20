<script lang="ts">
	import { onMount } from 'svelte';
	import { Search, History, X, SlidersHorizontal } from 'lucide-svelte';
	import {
		searchStore,
		searchHistory,
		executeSearch,
		loadFilterOptions
	} from '$lib/stores/search.js';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import FacetFilters from '$lib/components/FacetFilters.svelte';

	// Local state
	let showHistory = $state(false);
	let showMobileFilters = $state(false);
	let searchInput: HTMLInputElement;

	onMount(() => {
		loadFilterOptions();
		executeSearch();
	});

	function handleSearch() {
		showHistory = false;
		executeSearch();
	}


	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSearch();
		}
	}

	function handleHistorySelect(item: { query: string }) {
		searchStore.setQuery(item.query);
		showHistory = false;
		executeSearch();
	}

	function handleHistoryRemove(event: MouseEvent, query: string) {
		event.stopPropagation();
		searchHistory.remove(query);
	}

	function clearHistory() {
		searchHistory.clear();
		showHistory = false;
	}
</script>

<svelte:head>
	<title>Suche | MedWiss DB</title>
</svelte:head>

<div class="search-page">
	<header class="search-header">
		<h1>Wissensdatenbank durchsuchen</h1>
	</header>

	<div class="search-container">
		<!-- Search Input Area -->
		<div class="search-input-wrapper">
			<div class="search-input-container">
				<Search size={20} class="search-icon" />
				<input
					bind:this={searchInput}
					type="text"
					class="search-input"
					bind:value={$searchStore.query}
					onkeydown={handleKeyDown}
					onfocus={() => showHistory = $searchHistory.length > 0}
				/>
				{#if $searchStore.query}
					<button
						class="clear-input-btn"
						onclick={() => {
							searchStore.setQuery('');
							searchInput?.focus();
						}}
					>
						<X size={18} />
					</button>
				{/if}
				<button class="search-btn" onclick={handleSearch}>
					<span>Suchen</span>
				</button>
			</div>

			<!-- Search History Dropdown -->
			{#if showHistory && $searchHistory.length > 0}
				<div class="history-dropdown">
					<div class="history-header">
						<div class="history-title">
							<History size={16} />
							<span>Letzte Suchen</span>
						</div>
						<button class="clear-history-btn" onclick={clearHistory}>
							Alle löschen
						</button>
					</div>
					<div class="history-list">
						{#each $searchHistory as item (item.query)}
							<div
								class="history-item"
								role="button"
								tabindex="0"
								onclick={() => handleHistorySelect(item)}
								onkeydown={(e) => e.key === 'Enter' && handleHistorySelect(item)}
							>
								<span class="history-query">{item.query}</span>
								<button
									class="history-remove-btn"
									onclick={(e) => handleHistoryRemove(e, item.query)}
								>
									<X size={14} />
								</button>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<button
			class="mobile-filter-toggle"
			onclick={() => showMobileFilters = !showMobileFilters}
		>
			<SlidersHorizontal size={18} />
			<span>Filter</span>
			{#if Object.values($searchStore.filters).some((v) => v !== '')}
				<span class="filter-indicator"></span>
			{/if}
		</button>

		<div class="search-body">
			<aside class="filters-sidebar" class:mobile-open={showMobileFilters}>
				<button
					class="mobile-filter-close"
					aria-label="Filter schließen"
					onclick={() => showMobileFilters = false}
				>
					<X size={20} />
				</button>
				<FacetFilters />
			</aside>
			<div class="results-area">
				<SearchResults />
			</div>
		</div>
	</div>
</div>

<!-- Click outside to close history -->
<svelte:window onclick={(e) => {
	if (showHistory && !(e.target as Element)?.closest('.search-input-wrapper')) {
		showHistory = false;
	}
}} />

<style>
	.search-page {
		max-width: 1400px;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
	}

	.search-body {
		display: grid;
		grid-template-columns: 280px minmax(0, 1fr);
		gap: var(--space-6);
		align-items: start;
	}

	.filters-sidebar {
		position: sticky;
		top: var(--space-4);
	}

	.search-header {
		text-align: center;
		margin-bottom: var(--space-8);
	}

	.search-header h1 {
		font-size: var(--font-size-3xl);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-2);
	}

	.search-container {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.search-input-wrapper {
		position: relative;
	}

	.search-input-container {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		background: var(--color-background-primary);
		border: 2px solid var(--color-border);
		border-radius: var(--radius-xl);
		padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4);
		transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
	}

	.search-input-container:focus-within {
		border-color: var(--color-primary);
		box-shadow: var(--shadow-focus);
	}

	:global(.search-icon) {
		color: var(--color-text-tertiary);
		flex-shrink: 0;
	}

	.search-input {
		flex: 1;
		border: none;
		background: none;
		font-size: var(--font-size-lg);
		color: var(--color-text-primary);
		padding: var(--space-2) 0;
		min-width: 0;
	}

	.search-input::placeholder {
		color: var(--color-text-tertiary);
	}

	.search-input:focus {
		outline: none;
	}

	.clear-input-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		background: var(--color-background-tertiary);
		color: var(--color-text-secondary);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
		flex-shrink: 0;
	}

	.clear-input-btn:hover {
		background: var(--color-error-subtle);
		color: var(--color-error);
	}

	.search-btn {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius-lg);
		font-weight: var(--font-weight-semibold);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: background var(--transition-fast);
		flex-shrink: 0;
	}

	.search-btn:hover {
		background: var(--color-primary-dark);
	}

	/* History Dropdown */
	.history-dropdown {
		position: absolute;
		top: calc(100% + var(--space-2));
		left: 0;
		right: 0;
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		z-index: 100;
		overflow: hidden;
	}

	.history-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
	}

	.history-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-secondary);
	}

	.clear-history-btn {
		font-size: var(--font-size-xs);
		color: var(--color-text-tertiary);
		background: none;
		border: none;
		cursor: pointer;
		transition: color var(--transition-fast);
	}

	.clear-history-btn:hover {
		color: var(--color-error);
	}

	.history-list {
		max-height: 300px;
		overflow-y: auto;
	}

	.history-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		width: 100%;
		padding: var(--space-3) var(--space-4);
		background: none;
		border: none;
		cursor: pointer;
		transition: background var(--transition-fast);
		text-align: left;
	}

	.history-item:hover {
		background: var(--color-background-secondary);
	}

	.history-query {
		flex: 1;
		font-size: var(--font-size-sm);
		color: var(--color-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.history-remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border: none;
		background: none;
		color: var(--color-text-tertiary);
		border-radius: var(--radius-sm);
		cursor: pointer;
		flex-shrink: 0;
	}

	.mobile-filter-close {
		display: none;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		padding: 0;
		background: var(--color-background-primary);
		color: var(--color-text-secondary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-full);
		cursor: pointer;
		flex-shrink: 0;
		transition: background var(--transition-fast), color var(--transition-fast);
	}

	.mobile-filter-close:hover {
		background: var(--color-error-subtle);
		color: var(--color-error);
	}

	.mobile-filter-toggle {
		display: none;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-4);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		font-size: var(--font-size-sm);
		cursor: pointer;
		align-self: flex-start;
	}

	.filter-indicator {
		width: 8px;
		height: 8px;
		background: var(--color-primary);
		border-radius: 50%;
	}

	.results-area {
		min-width: 0;
	}

	@media (max-width: 768px) {
		.search-page {
			padding: var(--space-4);
		}

		.search-header h1 {
			font-size: var(--font-size-2xl);
		}

		.search-input-container {
			flex-wrap: wrap;
		}

		.search-btn span {
			display: none;
		}

		.search-body {
			grid-template-columns: 1fr;
		}

		.mobile-filter-toggle {
			display: flex;
		}

		.filters-sidebar {
			display: none;
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			background: rgba(0, 0, 0, 0.5);
			z-index: 200;
			padding: var(--space-4);
		}

		.filters-sidebar.mobile-open {
			display: flex;
			flex-direction: column;
			gap: var(--space-3);
		}

		.mobile-filter-close {
			display: flex;
			align-self: flex-end;
		}

		.filters-sidebar :global(.facet-filters) {
			flex: 1;
			min-height: 0;
			overflow-y: auto;
		}
	}
</style>
