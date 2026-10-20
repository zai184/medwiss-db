<script lang="ts">
	import { onMount } from 'svelte';
	import {
		Folder, FileText, ChevronRight,
		Search, X, CornerUpLeft, HardDrive
	} from 'lucide-svelte';
	import { openBrowseEntry } from '$lib/stores/entryViewer.js';
	import { entriesApi, type EntryResponse } from '$lib/api';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	// Path of the currently-viewed folder in the right pane (array of node names).
	// Persisted to sessionStorage (not the URL/history API — SvelteKit owns history)
	// so the browser back button from an opened entry returns to this folder.
	const savedPath =
		typeof window !== 'undefined'
			? JSON.parse(sessionStorage.getItem('bibliothek-path') ?? 'null')
			: null;
	let currentPath = $state<string[]>(Array.isArray(savedPath) ? savedPath : []);

	// --- Category labels / colors ----------------------------------------------

	const displayNameMap: Record<string, string> = {
		sop: 'SOPs', leitlinien: 'Leitlinien', studien: 'Studien', red_flags: 'Red Flags',
		frageboegen: 'Fragebögen', nachschlagen: 'Nachschlagen', infoblaetter: 'Infoblätter',
		faecher: 'Fächer', faelle: 'Fälle', pharma: 'Pharma', fortbildung: 'Fortbildung',
		pruefungen: 'Prüfungen', unbekannt: 'Unkategorisiert', notfall: 'Notfall'
	};
	const colorMap: Record<string, string> = {
		sop: '#10B981', leitlinien: '#3B82F6', studien: '#8B5CF6', red_flags: '#F97316',
		frageboegen: '#EAB308', nachschlagen: '#6B7280', infoblaetter: '#14B8A6',
		faecher: '#3B82F6', faelle: '#F97316', pharma: '#06B6D4', fortbildung: '#84CC16',
		pruefungen: '#A855F7', unbekannt: '#6B7280', notfall: '#EF4444'
	};

	// --- Tree model ------------------------------------------------------------
	interface FsNode {
		name: string;              // display name
		key: string;               // stable discriminator
		count: number;             // total docs under this node (incl. descendants)
		entries: EntryResponse[];  // docs directly in this folder
		children: Map<string, FsNode>;
	}

	let rootFolders = $state<FsNode[]>([]);

	function recount(node: FsNode): number {
		let total = node.entries.length;
		for (const child of node.children.values()) total += recount(child);
		node.count = total;
		return total;
	}

	// Raw folder segments of an entry, rooted at its source folder (e.g.
	// "3_Leitlinien/AWMF_Leitlinien/DGMKG_..." ). Preserves original names.
	function rawFolderSegments(entry: EntryResponse): string[] {
		const parts = (entry.source_path || '').split('/').filter(Boolean);
		// Source folders: `\d+_`-prefixed (1_SOPs, 3_Leitlinien, ...) or the
		// unnumbered Fortbildung convention (Fortbildung 2024/2025/2026, ...).
		const start = parts.findIndex(s => /^(\d+_|Fortbildung|Red\s?Flags|Flags)/.test(s));
		if (start === -1) return [];
		return parts.slice(start);
	}

	function buildTree(entries: EntryResponse[]): FsNode[] {
		const byRoot = new Map<string, FsNode>();

		for (const entry of entries) {
			const segs = rawFolderSegments(entry);
			if (segs.length === 0) continue;
			const rootName = segs[0];

			let root = byRoot.get(rootName);
			if (!root) {
				root = { name: rootName, key: `root|${rootName}`, count: 0, entries: [], children: new Map() };
				byRoot.set(rootName, root);
			}

			let node = root;
			// segs[0] is the root folder; segs[last] is the filename; the rest
			// are subfolders. Build the folder chain, then attach the file to
			// the folder it lives in.
			for (let i = 1; i < segs.length - 1; i++) {
				const seg = segs[i];
				if (!node.children.has(seg)) {
					node.children.set(seg, { name: seg, key: `${node.key}/${seg}`, count: 0, entries: [], children: new Map() });
				}
				node = node.children.get(seg)!;
			}
			node.entries.push(entry);
		}

		for (const root of byRoot.values()) recount(root);

		return [...byRoot.values()].sort((a, b) => {
			const na = parseInt(a.name, 10);
			const nb = parseInt(b.name, 10);
			if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
			return a.name.localeCompare(b.name, 'de');
		});
	}

	function sortedChildren(node: FsNode): FsNode[] {
		return [...node.children.values()].sort((a, b) => a.name.localeCompare(b.name, 'de'));
	}

	// Files in a folder, sorted by title (folders are always listed first)
	function sortedFiles(node: FsNode): EntryResponse[] {
		return [...node.entries].sort((a, b) => a.titel.localeCompare(b.titel, 'de'));
	}

	function nodeByPath(path: string[]): FsNode | null {
		if (path.length === 0) return null;
		const root = rootFolders.find(r => r.name === path[0]);
		if (!root) return null;
		let node = root;
		for (let i = 1; i < path.length; i++) {
			const next = node.children.get(path[i]);
			if (!next) return null;
			node = next;
		}
		return node;
	}

	// --- Search helpers ----------------------------------------------------------
	function matchesEntry(entry: EntryResponse, q: string): boolean {
		return entry.titel.toLowerCase().includes(q) ||
			(entry.zusammenfassung?.toLowerCase().includes(q) ?? false) ||
			(entry.quelle?.toLowerCase().includes(q) ?? false);
	}
	// Flatten ALL entries across the entire tree that match the query
	function flattenAllMatches(q: string): EntryResponse[] {
		const out: EntryResponse[] = [];
		function walk(node: FsNode) {
			for (const e of node.entries) if (matchesEntry(e, q)) out.push(e);
			for (const c of node.children.values()) walk(c);
		}
		for (const root of rootFolders) walk(root);
		return out.sort((a, b) => a.titel.localeCompare(b.titel, 'de'));
	}

	const allMatches = $derived(
		searchQuery.trim() ? flattenAllMatches(searchQuery.trim().toLowerCase()) : []
	);

	const totalDocs = $derived(
		rootFolders.reduce((sum, r) => sum + r.count, 0)
	);

	// --- Navigation --------------------------------------------------------------
	function navigateTo(path: string[]) { currentPath = path; }

	// Persist the current folder so a history.back() remount restores it.
	$effect(() => {
		sessionStorage.setItem('bibliothek-path', JSON.stringify(currentPath));
	});
	function openRoot(name: string) { navigateTo([name]); }
	function openFolder(name: string) { navigateTo([...currentPath, name]); }
	function goUp() { if (currentPath.length > 0) navigateTo(currentPath.slice(0, -1)); }
	function openEntry(entry: EntryResponse, list?: EntryResponse[]) {
		const clickable = (e: EntryResponse) => ({ id: e.id, title: e.titel, source_path: e.source_path });
		openBrowseEntry(clickable(entry), list?.map(clickable));
	}
	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
	}
	function clearSearch() { searchQuery = ''; }

	// Display name: strip a leading numeric folder prefix ("1_SOPs" -> "SOPs")
	// and present underscores as spaces ("Red_Flags" -> "Red Flags")
	function displayName(name: string): string {
		return name.replace(/^\d+_/, '').replace(/_/g, ' ');
	}

	// File type label from the source path's extension ("x.pdf" -> "PDF").
	// Returns null when the path has no extension.
	function fileTypeLabel(path: string | null | undefined): string | null {
		const name = (path ?? '').split('/').pop() ?? '';
		const dot = name.lastIndexOf('.');
		if (dot <= 0 || dot === name.length - 1) return null;
		return name.slice(dot + 1).toUpperCase();
	}

	// Short path for search results: show the folder hierarchy portion
	function shortPath(sourcePath: string): string {
		const segs = rawFolderSegments({ source_path: sourcePath } as EntryResponse);
		// Drop the first segment (root folder) and the last (filename), show the rest
		if (segs.length <= 2) return displayName(segs[0] || '');
		return segs.slice(0, -1).map(displayName).join(' / ');
	}

	// Normalization strips digit prefixes and underscores, lowercases, removes
	// diacritics (ä->a, ö->o, ü->u) and collapses ae/oe/ue transliterations so
	// "Red_Flags"/"Red Flags", "Fragebögen"/"Frageboegen", "Fächer"/"Faecher",
	// "Notfall" all resolve to their accent color instead of the gray fallback.
	function normalizeKey(s: string): string {
		return s
			.replace(/^\d+_/, '')        // numeric folder prefix ("2_Notfall")
			.replace(/_/g, ' ')          // "Red_Flags" -> "Red Flags"
			.toLowerCase()
			.normalize('NFD')
			.replace(/[\u0300-\u036f]/g, '') // strip combining marks (ä->a, ö->o, ü->u)
			.replace(/ß/g, 'ss')
			.replace(/ae/g, 'a')
			.replace(/oe/g, 'o')
			.replace(/ue/g, 'u');
	}

	// Color for a top-level folder tile/row. Matches a raw folder name like
	// "3_Leitlinien" or "5_Fächer" to a category color by comparing the
	// normalized leaf name (e.g. "Leitlinien") to known category labels.
	function rootColor(name: string): string {
		const leaf = normalizeKey(name);
		for (const [k, label] of Object.entries(displayNameMap)) {
			if (normalizeKey(label) === leaf) return colorMap[k];
		}
		// fallback: substring match ("Red_Flags" -> red_flags)
		for (const [k, label] of Object.entries(displayNameMap)) {
			const l = normalizeKey(label);
			if (leaf.includes(l) || l.includes(leaf)) {
				if (leaf.length >= 3) return colorMap[k];
			}
		}
		return '#6b7280';
	}

	async function loadEntries() {
		try {
			loading = true;
			error = null;
			const response = await entriesApi.getAll({ limit: 10000 });
			rootFolders = buildTree(response.items);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unbekannter Fehler';
		} finally {
			loading = false;
		}
	}

	onMount(async () => { await loadEntries(); });
</script>

<svelte:head>
	<title>Bibliothek | MedWiss DB</title>
</svelte:head>

<div class="fm-page">
	<header class="fm-header">
		<div class="header-title">
			<HardDrive size={24} />
			<div>
				<h1>Bibliothek</h1>
				<p class="subtitle">{totalDocs} Dokumente</p>
			</div>
		</div>
		<div class="search-box">
			<Search size={18} />
			<input type="text" bind:value={searchQuery} />
			{#if searchQuery}
				<button class="search-clear" onclick={clearSearch} title="Suche löschen"><X size={16} /></button>
			{/if}
		</div>
	</header>

	{#if loading}
		<div class="loading-state"><div class="spinner"></div><span>Lade Bibliothek...</span></div>
	{:else if error}
		<div class="error-state"><p>{error}</p><button onclick={loadEntries}>Erneut versuchen</button></div>
	{:else}
		<div class="fm">
			<section class="fm-content">
				<div class="fm-breadcrumb">
					<button class="up-btn" onclick={goUp} disabled={currentPath.length === 0} title="Höher"><CornerUpLeft size={16} /></button>
					<button class="crumb" class:crumb-active={currentPath.length === 0}
						onclick={() => navigateTo([])}>Wissensdatenbank</button>
					{#each currentPath as seg, i}
						<span class="crumb-sep">/</span>
						<button class="crumb" class:crumb-active={i === currentPath.length - 1}
							onclick={() => navigateTo(currentPath.slice(0, i + 1))}>{displayName(seg)}</button>
					{/each}
				</div>

				{#if searchQuery.trim()}
					<!-- Search: show matching files across all folders -->
					<div class="fm-listing">
						{#each allMatches as file}
							<button class="file-row" onclick={() => openEntry(file, allMatches)}>
								<FileText size={18} class="file-row-icon" />
								<span class="file-row-name">{file.titel}</span>
								{#if file.source_path}
									<span class="file-row-path">{shortPath(file.source_path)}</span>
								{/if}
								<span class="file-row-date">{formatDate(file.created_at)}</span>
							</button>
						{:else}
							<div class="empty-state"><p>Keine passenden Dateien</p></div>
						{/each}
					</div>
				{:else if currentPath.length === 0}
					<!-- Root: category tiles -->
					<div class="folder-grid">
						{#each rootFolders as root}
							<button class="folder-tile" style="--fc: {rootColor(root.name)}" onclick={() => openRoot(root.name)}>
								<div class="folder-tile-icon"><Folder size={26} /></div>
								<div class="folder-tile-name">{displayName(root.name)}</div>
								<div class="folder-tile-count">{root.count} Dateien</div>
							</button>
						{/each}
					</div>
				{:else}
					{@const node = nodeByPath(currentPath)}
					{#if node}
						<div class="fm-listing">
							{#each sortedChildren(node) as child}
								<button class="folder-row" onclick={() => openFolder(child.name)}>
									<Folder size={20} class="folder-row-icon" />
									<span class="folder-row-name">{displayName(child.name)}</span>
									<span class="folder-row-count">{child.count}</span>
									<ChevronRight size={16} class="folder-row-arrow" />
								</button>
							{/each}
							{#each sortedFiles(node) as file}
								<button class="file-row" onclick={() => openEntry(file, sortedFiles(node))}>
									<FileText size={18} class="file-row-icon" />
									<span class="file-row-name">{file.titel}</span>
									{#if file.quelle}<span class="file-badge">{fileTypeLabel(file.source_path) ?? 'Datei'}</span>{/if}
									<span class="file-row-date">{formatDate(file.created_at)}</span>
								</button>
							{/each}
							{#if sortedChildren(node).length === 0 && node.entries.length === 0}
								<div class="empty-state"><p>Dieser Ordner ist leer</p></div>
							{/if}
						</div>
					{:else}
						<div class="empty-state"><p>Ordner nicht gefunden</p></div>
					{/if}
				{/if}
			</section>
		</div>
	{/if}
</div>

<style>
	.fm-page { max-width: 1000px; margin: 0 auto; padding: var(--space-6) var(--space-4); }
	.fm-header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-6); }
	.header-title { display: flex; align-items: center; gap: var(--space-3); }
	.header-title h1 { font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
	.subtitle { font-size: var(--font-size-sm); color: var(--color-text-secondary); }
	.search-box { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--color-background-primary); border: 1px solid var(--color-border); border-radius: var(--radius-lg); flex: 1; max-width: 420px; min-width: 220px; }
	.search-box input { flex: 1; border: none; background: none; font-size: var(--font-size-base); color: var(--color-text-primary); outline: none; }
	.search-box input::placeholder { color: var(--color-text-tertiary); }
	.search-clear { background: none; border: none; color: var(--color-text-tertiary); cursor: pointer; display: flex; padding: 2px; }

	.loading-state { display: flex; flex-direction: column; align-items: center; padding: var(--space-12); gap: var(--space-4); color: var(--color-text-secondary); }
	.spinner { width: 40px; height: 40px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }
	.error-state { text-align: center; padding: var(--space-12); color: var(--color-error); }
	.error-state button { margin-top: var(--space-4); padding: var(--space-2) var(--space-4); background: var(--color-primary); color: white; border: none; border-radius: var(--radius-md); cursor: pointer; }
	.empty-state { text-align: center; padding: var(--space-8); color: var(--color-text-secondary); }

	/* File manager */
	.fm { min-height: 60vh; }
	.fm-content { min-width: 0; background: var(--color-background-primary); border: 1px solid var(--color-border); border-radius: var(--radius-lg); overflow: hidden; }
	.fm-breadcrumb { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--color-border); font-size: var(--font-size-sm); color: var(--color-text-secondary); flex-wrap: wrap; }
	.up-btn { background: none; border: none; color: var(--color-text-secondary); cursor: pointer; display: flex; align-items: center; padding: 0 var(--space-1); border-radius: var(--radius-sm); }
	.up-btn:disabled { color: var(--color-text-tertiary); cursor: default; }
	.up-btn:hover:not(:disabled) { background: var(--color-background-tertiary); }
	.crumb { background: none; border: none; color: var(--color-text-secondary); cursor: pointer; font-family: inherit; font-size: var(--font-size-sm); padding: 0 var(--space-1); border-radius: var(--radius-sm); }
	.crumb:hover { background: var(--color-background-tertiary); }
	.crumb-active { color: var(--color-primary); font-weight: var(--font-weight-semibold); }
	.crumb-sep { color: var(--color-text-tertiary); }

	/* Root folder tiles */
	.folder-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: var(--space-3); padding: var(--space-4); }
	.folder-tile { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-1); padding: var(--space-4); aspect-ratio: 1 / 1; min-width: 0; overflow: hidden; background: var(--color-background-secondary); border: 1px solid var(--color-border); border-radius: 0; cursor: pointer; transition: all var(--transition-fast); text-align: center; font-family: inherit; }
	.folder-tile:hover { border-color: var(--fc, var(--color-primary)); box-shadow: var(--shadow-sm); }
	.folder-tile-icon { color: var(--fc, var(--color-primary)); display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 44px; height: 44px; background: var(--fc, var(--color-primary)) 12%; border-radius: var(--radius-md); }
	.folder-tile-name { font-weight: var(--font-weight-semibold); color: var(--color-text-primary); font-size: var(--font-size-sm); min-width: 0; max-width: 100%; overflow: hidden; display: -webkit-box; line-clamp: 2; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
	.folder-tile-count { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }

	/* Folder + file rows */
	.fm-listing { padding: var(--space-2) var(--space-3) var(--space-3); display: flex; flex-direction: column; }
	.folder-row, .file-row { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); cursor: pointer; background: none; border: none; width: 100%; max-width: 100%; min-width: 0; text-align: left; font-family: inherit; transition: background var(--transition-fast); }
	.folder-row:hover, .file-row:hover { background: var(--color-background-tertiary); }
	/* :global — classes are passed through lucide components, scoped CSS can't reach them */
	:global(.folder-row-icon) { color: var(--color-primary); flex-shrink: 0; }
	.folder-row-name { font-weight: var(--font-weight-semibold); color: var(--color-text-primary); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: var(--font-size-sm); }
	.folder-row-count { font-size: var(--font-size-xs); color: var(--color-text-tertiary); }
	:global(.folder-row-arrow) { color: var(--color-text-tertiary); flex-shrink: 0; }
	:global(.file-row-icon) { color: var(--color-text-tertiary); flex-shrink: 0; }
	.file-row-name { font-size: var(--font-size-sm); color: var(--color-text-primary); flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.file-row-path { font-size: var(--font-size-xs); color: var(--color-text-tertiary); flex-shrink: 0; white-space: nowrap; }
	.file-badge { font-size: var(--font-size-xs); color: var(--color-primary); font-weight: var(--font-weight-medium); background: var(--color-primary-subtle); padding: 1px 6px; border-radius: var(--radius-sm); flex-shrink: 0; }
	.file-row-date { font-size: var(--font-size-xs); color: var(--color-text-tertiary); flex-shrink: 0; white-space: nowrap; }

	@media (max-width: 768px) {
		.fm-page { padding: var(--space-4); }
		.fm-content { min-width: 0; }
		.fm-listing { min-width: 0; overflow-x: hidden; }
		.folder-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
</style>
