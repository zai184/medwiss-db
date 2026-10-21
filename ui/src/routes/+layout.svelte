<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { Home, Search, PlusCircle, Shield, Library, FileText, PanelLeftClose, PanelLeftOpen, BookOpen, Link, Newspaper, Calculator, Siren } from 'lucide-svelte';
	import EntryViewerOverlay from '$lib/components/EntryViewerOverlay.svelte';

	let { children } = $props();

	let appVersion = $state('');

	// Leitlinien page disabled via build-time env flag (VPS deploy; broken there).
	const leitlinienDisabled = import.meta.env.VITE_DISABLE_LEITLINIEN === '1';

	$effect(() => {
		fetch('/api/v1/version')
			.then((r) => (r.ok ? r.json() : null))
			.then((d) => (appVersion = (d?.version ?? '').replace(/^v/, '')))
			.catch(() => {});
	});

	let collapsed = $state(false);
	let menuHidden = $state(false);
	let lastScrollY = 0;

	try {
		if (typeof localStorage !== 'undefined') {
			collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
		}
	} catch {
		/* ignore storage errors */
	}

	// Auto-hide the mobile top menu: hide while scrolling down, show on scroll up.
	if (typeof window !== 'undefined') {
		window.addEventListener('scroll', () => {
			const y = window.scrollY;
			menuHidden = y > lastScrollY && y > 100;
			lastScrollY = y;
		}, { passive: true });
	}

	function toggleSidebar() {
		collapsed = !collapsed;
		try {
			localStorage.setItem('sidebar-collapsed', String(collapsed));
		} catch {
			/* ignore storage errors */
		}
	}
</script>

<div class="app">
	<nav class="sidebar" class:collapsed={collapsed} class:menu-hidden={menuHidden}>
		<div class="sidebar-header">
			<div class="logo">
				<div class="logo-icon">M</div>
				<span class="logo-text">MedWiss {#if appVersion}<span class="version" title="aus pyproject.toml">{appVersion}</span>{/if}</span>
			</div>
			<button
				class="sidebar-toggle"
				onclick={toggleSidebar}
				title={collapsed ? 'Menü erweitern' : 'Menü einklappen'}
				aria-label={collapsed ? 'Menü erweitern' : 'Menü einklappen'}
			>
				{#if collapsed}
					<PanelLeftOpen size={18} />
				{:else}
					<PanelLeftClose size={18} />
				{/if}
			</button>
		</div>
		
		<div class="nav-section">
			<span class="nav-label">Hauptmenü</span>
			<a href="/" class="nav-item" class:active={$page.url.pathname === '/'}>
				<Home size={18} />
				<span>Dashboard</span>
			</a>
			<a href="/search" class="nav-item" class:active={$page.url.pathname === '/search'}>
				<Search size={18} />
				<span>Suche</span>
			</a>
			{#if !leitlinienDisabled}
			<a href="/leitlinien" class="nav-item" class:active={$page.url.pathname === '/leitlinien'}>
				<FileText size={18} />
				<span>Leitlinien</span>
			</a>
			{/if}
			<a href="/bibliothek" class="nav-item" class:active={$page.url.pathname === '/bibliothek'}>
				<Library size={18} />
				<span>Bibliothek</span>
			</a>
			<a href="/eingabe" class="nav-item mobile-hidden">
				<PlusCircle size={18} />
				<span>Neuer Eintrag</span>
			</a>
		</div>

		<div class="nav-section">
			<span class="nav-label">Referenz</span>
			<a href="/referenz" class="nav-item" class:active={$page.url.pathname.startsWith('/referenz')}>
				<Link size={18} />
				<span>Links</span>
			</a>
			<a href="/pubmed" class="nav-item" class:active={$page.url.pathname.startsWith('/pubmed')}>
				<Newspaper size={18} />
				<span>PubMed</span>
			</a>
			<a href="/icd11" class="nav-item" class:active={$page.url.pathname.startsWith('/icd11')}>
				<BookOpen size={18} />
				<span>ICD-11</span>
			</a>
		<a href="/rechner" class="nav-item" class:active={$page.url.pathname.startsWith('/rechner')}>
			<Calculator size={18} />
			<span>Rechner</span>
		</a>
		<a href="/notfall" class="nav-item" class:active={$page.url.pathname.startsWith('/notfall')}>
			<Siren size={18} />
			<span>Notfall</span>
		</a>
		</div>

		<div class="nav-section">
			<span class="nav-label">System</span>
			<a href="/admin" class="nav-item admin-only" class:active={$page.url.pathname.startsWith('/admin')}>
				<Shield size={20} />
				<span>Admin</span>
			</a>
		</div>
	</nav>
	
	<main class="main-content">
		{@render children()}
	</main>
</div>

<footer class="site-disclaimer">
	Nur zu Lern- und Referenzzwecken — keine medizinische Beratung, kein Ersatz für
	ärztliches Fachpersonal. Im Notfall: 112. Alle Angaben ohne Gewähr.
	<a href="https://github.com/zai184/medwiss-db">Quellcode (AGPL-3.0)</a>
</footer>

<EntryViewerOverlay />

<style>
	.site-disclaimer {
		max-width: 900px;
		margin: 0 auto;
		padding: var(--space-4) var(--space-6);
		font-size: var(--font-size-xs);
		color: var(--color-text-secondary);
		text-align: center;
	}

	.app {
		display: flex;
		min-height: 100vh;
	}
	
	.sidebar {
		width: 260px;
		background: var(--color-background-primary);
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		position: fixed;
		top: 0;
		left: 0;
		bottom: 0;
		z-index: 100;
		transition: width var(--transition-fast);
	}
	
	.sidebar-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
		padding: var(--space-5);
		border-bottom: 1px solid var(--color-border);
	}

	.sidebar-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		flex-shrink: 0;
		background: transparent;
		color: var(--color-text-tertiary);
		border: none;
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.sidebar-toggle:hover {
		background: var(--color-background-tertiary);
		color: var(--color-text-primary);
	}
	
	.logo {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}
	
	.logo-icon {
		width: 40px;
		height: 40px;
		background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
		color: white;
		border-radius: var(--radius-lg);
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: var(--font-weight-bold);
		font-size: var(--font-size-xl);
	}
	
	.logo-text {
		font-size: var(--font-size-xl);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
	}
	

	.version {
		font-size: 0.65rem;
		font-weight: 400;
		color: var(--color-text-secondary, #888);
		vertical-align: super;
		margin-left: 0.3em;
		user-select: none;
	}
	.nav-section {
		padding: var(--space-4);
	}
	
	.nav-section + .nav-section {
		border-top: 1px solid var(--color-border);
	}
	
	.nav-label {
		display: block;
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--color-text-tertiary);
		padding: var(--space-3) var(--space-3);
		margin-bottom: var(--space-1);
	}
	
	.nav-item {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		text-decoration: none;
		transition: all var(--transition-fast);
		margin-bottom: var(--space-1);
	}
	
	.nav-item:hover {
		background: var(--color-background-tertiary);
		color: var(--color-text-primary);
	}
	
	.nav-item.active {
		background: var(--color-primary-subtle);
		color: var(--color-primary);
	}
	
	.main-content {
		flex: 1;
		margin-left: 260px;
		min-height: 100vh;
		transition: margin-left var(--transition-fast);
	}

	/* Collapsed sidebar */
	.sidebar.collapsed {
		width: 74px;
	}

	.sidebar.collapsed .sidebar-header {
		padding: var(--space-4) var(--space-3);
	}

	.sidebar.collapsed .logo {
		flex: 1;
		justify-content: center;
	}

	.sidebar.collapsed .logo-text,
	.sidebar.collapsed .nav-label,
	.sidebar.collapsed .nav-item span {
		display: none;
	}

	.sidebar.collapsed .nav-section {
		padding: var(--space-3) var(--space-2);
	}

	.sidebar.collapsed .nav-section + .nav-section {
		margin-top: var(--space-1);
	}

	.sidebar.collapsed .nav-item {
		justify-content: center;
		gap: 0;
		padding: var(--space-3);
	}

	.sidebar.collapsed ~ .main-content {
		margin-left: 74px;
	}
	
	/* Mobile: top nav bar, auto-hide on scroll down, fits viewport width */
	@media (max-width: 768px) {
		.sidebar {
			width: 100%;
			max-width: 100vw;
			height: auto;
			position: fixed;
			top: 0;
			bottom: auto;
			left: 0;
			right: 0;
			box-sizing: border-box;
			border-right: none;
			border-top: none;
			border-bottom: 1px solid var(--color-border);
			flex-direction: row;
			padding: var(--space-2);
			z-index: 100;
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
			transition: transform var(--transition-fast), width var(--transition-fast);
		}

		/* Auto-hide: slide the bar off the top while scrolling down */
		.sidebar.menu-hidden {
			transform: translateY(-100%);
		}

		.sidebar-header,
		.nav-label {
			display: none;
		}

		.nav-section {
			display: contents;
		}

		.nav-section + .nav-section {
			border-top: none;
		}

		.nav-item {
			flex-direction: column;
			align-items: center;
			gap: var(--space-1);
			padding: var(--space-1);
			font-size: var(--font-size-xs);
			flex: 1 1 0;
			min-width: 0;
		}

		.nav-item span {
			font-size: 10px;
			max-width: 100%;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}

		/* Hide items that don't work / need work on mobile */
		.mobile-hidden,
		.admin-only {
			display: none;
		}

		.main-content {
			margin-left: 0;
			margin-top: 60px;
			margin-bottom: 0;
			min-width: 0;
			max-width: 100vw;
			overflow-x: hidden;
			transition: margin-top var(--transition-fast);
		}

		/* Reclaim the bar's space once it auto-hides */
		.sidebar.menu-hidden ~ .main-content {
			margin-top: 0;
		}

		/* Mobile: ignore collapsed state - always full-width top nav */
		.sidebar.collapsed {
			width: 100%;
		}

		.sidebar.collapsed .sidebar-header {
			display: none;
		}

		.sidebar.collapsed .nav-item {
			justify-content: initial;
			gap: var(--space-1);
			padding: var(--space-2);
		}

		.sidebar.collapsed .nav-item span {
			display: inline;
			font-size: 10px;
		}

		.sidebar.collapsed ~ .main-content {
			margin-left: 0;
			margin-top: 60px;
			margin-bottom: 0;
		}

		/* When collapsed state is ignored on mobile, still allow auto-hide reclaim */
		.sidebar.collapsed.menu-hidden ~ .main-content {
			margin-top: 0;
		}
	}
</style>
