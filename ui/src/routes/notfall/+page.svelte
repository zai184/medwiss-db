<script lang="ts">
	import FileViewer from '$lib/components/FileViewer.svelte';
	import { onMount } from 'svelte';
	import { FileText } from 'lucide-svelte';
	import { entriesApi, type EntryResponse } from '$lib/api';
	import { groupEntries, NOTFALL_GROUPS, type EntryGroup } from '$lib/notfallGroups';

	// Tabs are path-filtered views over the corpus ("files are the database"):
	// - Algorithmen: the curated .md quick-reference docs in 2_Notfall/00_Notfall_SOPs
	// - SOPs Notaufnahme: the SOP files in 1_SOPs/SOPs Notaufnahme
	// - Notfall-SOPs: non-md files (PDF/images) in 2_Notfall/00_Notfall_SOPs
	const TABS = [
		{ id: 'algos', label: 'Algorithmen', path: '2_Notfall/00_Notfall_SOPs', mdOnly: true },
		{ id: 'files', label: 'SOPs', path: '2_Notfall/00_Notfall_SOPs', mdOnly: false },
		{ id: 'sops', label: 'SOPs Notaufnahme', path: '1_SOPs/SOPs Notaufnahme', mdOnly: false },
	] as const;

	type TabId = (typeof TABS)[number]['id'];

	let active = $state<TabId>('algos');
	let entries = $state<Record<string, EntryResponse[]>>({});
	let loading = $state(true);
	let activeId = $state<number | null>(null);
	let tabErrors = $state<Record<string, string>>({});
	let filter = $state('');

	const mdSuffix = /\.(md|rst|txt)$/i;

	async function loadTab(tab: (typeof TABS)[number]) {
		if (entries[tab.id]) return;
		try {
			const resp = await entriesApi.getAll({ source_path: tab.path, limit: 1000 });
			const items = resp.items.filter((e) =>
				tab.mdOnly ? mdSuffix.test(e.source_path ?? '') : !mdSuffix.test(e.source_path ?? '')
			);
			items.sort((a, b) => a.titel.localeCompare(b.titel, 'de'));
			entries[tab.id] = items;
			delete tabErrors[tab.id];
		} catch (e: unknown) {
			tabErrors[tab.id] = e instanceof Error ? e.message : String(e);
			console.error(`Notfall-Tab "${tab.label}" konnte nicht geladen werden:`, e);
		}
	}

	async function retryTab() {
		const tab = TABS.find((t) => t.id === active)!;
		delete tabErrors[tab.id];
		await loadTab(tab);
	}

	onMount(async () => {
		await Promise.allSettled(TABS.map(loadTab));
		loading = false;
	});

	const visible = $derived.by(() => {
		const tab = TABS.find((t) => t.id === active)!;
		const items = entries[tab.id] ?? [];
		const t = filter.trim().toLowerCase();
		return t ? items.filter((e) => e.titel.toLowerCase().includes(t)) : items;
	});

	const activeTab = $derived(TABS.find((t) => t.id === active)!);
	const groups = $derived<EntryGroup[]>(
		activeTab.id in NOTFALL_GROUPS ? groupEntries(activeTab.id, visible) : []
	);

	const activeEntry = $derived.by(() => {
		if (activeId == null) return null;
		for (const items of Object.values(entries)) {
			const entry = items.find((e) => e.id === activeId);
			if (entry) return entry;
		}
		return null;
	});

	function closeViewer() {
		activeId = null;
	}

	$effect(() => {
		if (activeId == null) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') closeViewer();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<svelte:head>
	<title>Notfall | MedWiss DB</title>
</svelte:head>

<div class="notfall-page">
	<header class="page-header">
		<h1>Notfall</h1>
		<p class="subtitle">Leitlinien: <a href="https://www.erc.edu/science-research/guidelines/" target="_blank" rel="noopener noreferrer">ERC</a> · <a href="https://www.grc-org.de/wissenschaft/leitlinien" target="_blank" rel="noopener noreferrer">GRC</a> · <a href="https://wiederbelebung.at/leitlinien/" target="_blank" rel="noopener noreferrer">ARC</a></p>
	</header>

	<input
		class="filter-input"
		type="search"
		placeholder="Filtern …"
		bind:value={filter}
		aria-label="Einträge filtern"
	/>

	<div class="tabs" role="tablist">
		{#each TABS as tab (tab.id)}
			<button
				class="tab"
				class:active={active === tab.id}
				role="tab"
				aria-selected={active === tab.id}
				onclick={() => (active = tab.id)}
			>
				{tab.label}
				<span class="count">{entries[tab.id]?.length ?? '…'}</span>
			</button>
		{/each}
	</div>

	{#if loading}
		<p class="empty">Lade …</p>
	{:else if tabErrors[active]}
		<p class="empty">
			Fehler: {tabErrors[active]}
			<button class="retry" onclick={retryTab}>Erneut versuchen</button>
		</p>
	{:else if !visible.length}
		<p class="empty">Keine Einträge gefunden.</p>
	{:else if groups.length}
		{#each groups as group}
			<section class="entry-group">
				<h2 class="group-heading">
					{group.heading}
					<span class="group-count">{group.items.length}</span>
				</h2>
				<ul class="entry-list">
					{#each group.items as entry (entry.id)}
						<li class="entry-row">
							<button
								class="entry-link"
								title={`${entry.titel} öffnen`}
								onclick={() => (activeId = entry.id)}
							>
								<FileText size={16} />
								<span class="title">{entry.titel}</span>
							</button>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{:else}
		<ul class="entry-list">
			{#each visible as entry (entry.id)}
				<li class="entry-row">
					<button
						class="entry-link"
						title={`${entry.titel} öffnen`}
						onclick={() => (activeId = entry.id)}
					>
						<FileText size={16} />
						<span class="title">{entry.titel}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

{#if activeId != null}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="viewer-overlay"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) closeViewer();
		}}
	>
		<div class="viewer-panel" role="dialog" aria-modal="true" aria-label={activeEntry?.titel ?? 'Dateivorschau'}>
			<header class="viewer-header">
				<h2 class="viewer-title">{activeEntry?.titel ?? ''}</h2>
				<button type="button" class="viewer-close" aria-label="Schließen" onclick={closeViewer}>
					×
				</button>
			</header>
			<div class="viewer-body">
				<FileViewer entryId={activeId} />
			</div>
		</div>
	</div>
{/if}

<style>
	.notfall-page {
		max-width: 900px;
		margin: 0 auto;
		padding: var(--space-6) var(--space-4);
	}

	.page-header h1 {
		font-size: 1.8rem;
		margin: 0 0 0.25rem;
		font-family: 'Crimson Pro', Georgia, serif;
	}

	.subtitle {
		color: var(--color-text-secondary);
		margin: 0 0 var(--space-4);
	}

	.subtitle a {
		color: var(--color-primary);
	}

	.filter-input {
		width: 100%;
		max-width: 420px;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		font-family: inherit;
		background: var(--color-background-primary);
		color: var(--color-text-primary);
		margin-bottom: var(--space-4);
	}

	.filter-input:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: var(--shadow-focus);
	}

	.tabs {
		display: flex;
		gap: var(--space-2);
		flex-wrap: wrap;
		margin-bottom: var(--space-4);
	}

	.tab {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-full);
		background: var(--color-background-primary);
		color: var(--color-text-secondary);
		font-family: inherit;
		font-size: var(--font-size-sm);
		cursor: pointer;
	}

	.retry {
		margin-left: 0.5rem;
		padding: 0.2rem 0.7rem;
		border: 1px solid var(--color-primary);
		border-radius: var(--radius-md);
		background: var(--color-background-primary);
		color: var(--color-primary);
		font-family: inherit;
		cursor: pointer;
	}

	.tab:hover {
		border-color: var(--color-primary);
		color: var(--color-primary);
	}

	.tab.active {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: #ffffff;
	}

	.count {
		font-size: var(--font-size-xs);
		opacity: 0.75;
	}

	.entry-group {
		margin-bottom: var(--space-5);
	}

	.entry-group:last-child {
		margin-bottom: 0;
	}

	.group-heading {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		font-size: var(--font-size-md);
		font-weight: 600;
		color: var(--color-text-secondary);
		margin: 0 0 var(--space-2);
		padding-bottom: 0.4rem;
		border-bottom: 1px solid var(--color-border);
	}

	.group-count {
		font-size: var(--font-size-xs);
		opacity: 0.7;
		font-weight: 400;
	}

	.entry-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.entry-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		padding: 0.55rem 0.9rem;
	}

	.entry-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--color-text-primary);
		text-decoration: none;
		min-width: 0;
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		font: inherit;
		cursor: pointer;
		text-align: left;
		flex: 1 1 auto;
	}

	.entry-link:hover .title {
		color: var(--color-primary);
	}

	.viewer-overlay {
		position: fixed;
		inset: 0;
		z-index: 1000;
		display: flex;
		align-items: stretch;
		justify-content: center;
		padding: var(--space-4);
		background-color: rgba(0, 0, 0, 0.6);
	}

	.viewer-panel {
		position: relative;
		display: flex;
		flex-direction: column;
		width: 100%;
		max-width: 1100px;
		margin: 0 auto;
		background: var(--color-background-primary);
		color: var(--color-text-primary);
		border-radius: var(--radius-lg);
		border: 1px solid var(--color-border);
		box-shadow: var(--shadow-lg);
		overflow: hidden;
	}

	.viewer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-4);
		border-bottom: 1px solid var(--color-border);
		flex-shrink: 0;
	}

	.viewer-title {
		margin: 0;
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.viewer-close {
		flex-shrink: 0;
		width: 2.2rem;
		height: 2.2rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		background: var(--color-background-primary);
		color: var(--color-text-primary);
		font-size: 1.5rem;
		line-height: 1;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.viewer-close:hover {
		border-color: var(--color-primary);
		color: var(--color-primary);
	}

	.viewer-body {
		overflow: auto;
		padding: var(--space-4);
		height: 100%;
		min-height: 0;
	}

	@media (max-width: 768px) {
		.notfall-page {
			padding: var(--space-4);
		}
	}
</style>
