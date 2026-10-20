<script lang="ts">
	import { Filter, X, ChevronDown, ChevronUp, Check } from 'lucide-svelte';
	import { searchStore, executeSearch, type FilterOption } from '$lib/stores/search.js';

	interface FacetGroup {
		key: 'fachgebiet' | 'diagnose' | 'symptom' | 'dokumenttyp' | 'ordner_label' | 'folder';
		title: string;
		options: FilterOption[] | { name: string; count: number }[];
	}

	let expanded = $state({
		fachgebiet: false,
		diagnose: false,
		symptom: false,
		dokumenttyp: false,
		ordner_label: false,
		folder: false
	});

	const groups = $derived<FacetGroup[]>([
		{ key: 'fachgebiet', title: 'Fachgebiete', options: $searchStore.filterOptions.fachgebiete },
		{ key: 'diagnose', title: 'Diagnosen', options: $searchStore.filterOptions.diagnosen },
		{ key: 'symptom', title: 'Symptome', options: $searchStore.filterOptions.symptome },
		{ key: 'dokumenttyp', title: 'Dokumenttyp', options: $searchStore.filterOptions.dokumenttypen },
		{ key: 'ordner_label', title: 'Ordner-Labels', options: $searchStore.filterOptions.ordner_labels },
		{ key: 'folder', title: 'Ordner', options: $searchStore.filterOptions.folders }
	]);

	const activeCount = $derived(
		Object.values($searchStore.filters).filter((value) => value !== '').length
	);

	function toggleSection(key: FacetGroup['key']) {
		expanded[key] = !expanded[key];
	}

	function optionValue(option: FilterOption | { name: string; count: number }): string {
		return 'id' in option ? String(option.id) : option.name;
	}

	function isChecked(key: FacetGroup['key'], option: FilterOption | { name: string; count: number }): boolean {
		const current = $searchStore.filters[key];
		if (!current) return false;
		if ('id' in option && current === String(option.id)) return true;
		return current === option.name;
	}

	function handleToggle(key: FacetGroup['key'], option: FilterOption | { name: string; count: number }) {
		const value = optionValue(option);
		searchStore.setFilter(key, $searchStore.filters[key] === value ? '' : value);
		executeSearch();
	}

	function handleClear() {
		searchStore.clearFilters();
		executeSearch();
	}

	function handleApply() {
		executeSearch();
	}
</script>

<aside class="facet-filters">
	<div class="filters-header">
		<div class="filters-title">
			<Filter size={18} />
			<span>Filter</span>
			{#if activeCount > 0}
				<span class="filter-badge">{activeCount}</span>
			{/if}
		</div>
		{#if activeCount > 0}
			<button class="clear-btn" onclick={handleClear}>
				<X size={14} />
				<span>Zurücksetzen</span>
			</button>
		{/if}
	</div>

	<div class="filters-content">
		{#each groups as group (group.key)}
			{#if group.options.length > 0}
				<div class="filter-section">
					<button
						class="section-header"
						onclick={() => toggleSection(group.key)}
						aria-expanded={expanded[group.key]}
					>
						<span class="section-title">{group.title}</span>
						{#if expanded[group.key]}
							<ChevronUp size={16} />
						{:else}
							<ChevronDown size={16} />
						{/if}
					</button>
					{#if expanded[group.key]}
						<div class="checkbox-group">
							{#each group.options as option (option.name)}
								<button
									type="button"
									class="checkbox-label"
									class:is-checked={isChecked(group.key, option)}
									onclick={() => handleToggle(group.key, option)}
									role="checkbox"
									aria-checked={isChecked(group.key, option)}
								>
									<span class="tick-box" aria-hidden="true">
										{#if isChecked(group.key, option)}
											<Check size={12} strokeWidth={3} />
										{/if}
									</span>
									<span class="checkbox-text">
										{option.name}
										<span class="facet-count">({option.count})</span>
									</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		{/each}
	</div>

	<button class="apply-btn" onclick={handleApply}>
		Filter anwenden
	</button>
</aside>

<style>
	.facet-filters {
		background: var(--color-background-primary);
		border-radius: var(--radius-lg);
		border: 1px solid var(--color-border);
		padding: var(--space-4);
	}

	.filters-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--space-4);
		padding-bottom: var(--space-3);
		border-bottom: 1px solid var(--color-border);
	}

	.filters-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
	}

	.filter-badge {
		background: var(--color-primary);
		color: white;
		font-size: var(--font-size-xs);
		padding: 2px 6px;
		border-radius: var(--radius-full);
		min-width: 18px;
		text-align: center;
	}

	.clear-btn {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--color-text-secondary);
		background: none;
		border: none;
		cursor: pointer;
		transition: color var(--transition-fast);
	}

	.clear-btn:hover {
		color: var(--color-error);
	}

	.filters-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.filter-section {
		border-bottom: 1px solid var(--color-border);
		padding-bottom: var(--space-2);
	}

	.filter-section:last-of-type {
		border-bottom: none;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: var(--space-2) 0;
		background: none;
		border: none;
		cursor: pointer;
		color: var(--color-text-primary);
		font-weight: var(--font-weight-medium);
		font-size: var(--font-size-sm);
		transition: color var(--transition-fast);
	}

	.section-header:hover {
		color: var(--color-primary);
	}

	.checkbox-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-2) 0;
		padding-left: var(--space-2);
		max-height: 220px;
		overflow-y: auto;
	}

	.checkbox-label {
		display: flex;
		align-items: flex-start;
		gap: var(--space-2);
		width: 100%;
		padding: 0;
		margin: 0;
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
		font-size: var(--font-size-sm);
		font-family: inherit;
		color: var(--color-text-secondary);
		transition: color var(--transition-fast);
	}

	.checkbox-label:hover {
		color: var(--color-text-primary);
	}

	.tick-box {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		margin-top: 2px;
		flex-shrink: 0;
		border: 2px solid var(--color-border);
		border-radius: 3px;
		background: var(--color-background-primary);
		color: white;
	}

	.checkbox-label.is-checked .tick-box {
		border-color: var(--color-primary);
		background: var(--color-primary);
	}

	.checkbox-text {
		user-select: none;
	}

	.facet-count {
		color: var(--color-text-tertiary);
		font-size: var(--font-size-xs);
	}

	.apply-btn {
		width: 100%;
		margin-top: var(--space-4);
		padding: var(--space-3) var(--space-4);
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-weight: var(--font-weight-medium);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: background var(--transition-fast);
	}

	.apply-btn:hover {
		background: var(--color-primary-dark);
	}

	.apply-btn:active {
		transform: translateY(1px);
	}
</style>
