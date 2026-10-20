<script lang="ts">
	import FileViewer from './FileViewer.svelte';
	import { entryViewer } from '$lib/stores/entryViewer';
	import { afterNavigate } from '$app/navigation';

	const active = $derived($entryViewer);
	const multi = $derived(active != null && active.gallery.length > 1);

	let swipeStart: { x: number; y: number } | null = null;

	function handlePointerDown(e: PointerEvent) {
		if (!multi) return;
		const zoomed = (e.target as HTMLElement).closest('[data-zoomed="true"]') != null;
		swipeStart = zoomed ? null : { x: e.clientX, y: e.clientY };
	}

	function handlePointerUp(e: PointerEvent) {
		if (!swipeStart || !multi) return;
		const dx = e.clientX - swipeStart.x;
		const dy = e.clientY - swipeStart.y;
		swipeStart = null;
		if (Math.abs(dx) > 60 && Math.abs(dx) > 2 * Math.abs(dy)) {
			if (dx < 0) entryViewer.next();
			else entryViewer.prev();
		}
	}

	// Close on Escape while open; arrows navigate the gallery.
	$effect(() => {
		if ($entryViewer == null) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') entryViewer.close();
			if (e.key === 'ArrowRight') entryViewer.next();
			if (e.key === 'ArrowLeft') entryViewer.prev();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	// Leave any page (sidebar nav, Detail link, FileViewer edit/übernehmen flow)
	// closes the overlay so it never lingers on top of another route.
	afterNavigate(() => entryViewer.close());
</script>

{#if active != null}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="viewer-overlay"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) entryViewer.close();
		}}
	>
		<!-- Mobile browsers fire pointercancel instead of pointerup when they claim
			the touch as a scroll/gesture (common inside the fullscreen image scroll
			container); the cancel event still carries the final coordinates, so
			treat it as a swipe end too. -->
		<div
			class="viewer-panel"
			role="dialog"
			aria-modal="true"
			aria-label={active.entry.title}
			tabindex="-1"
			onpointerdown={handlePointerDown}
			onpointerup={handlePointerUp}
			onpointercancel={handlePointerUp}
		>
			<header class="viewer-header">
				<h2 class="viewer-title">{active.entry.title}</h2>
				{#if multi}
					<span class="gallery-count">{active.index + 1} / {active.gallery.length}</span>
				{/if}
				<div class="viewer-actions">
					<button
						type="button"
						class="viewer-close"
						aria-label="Schließen"
						onclick={() => entryViewer.close()}
					>
						×
					</button>
				</div>
			</header>
			<div class="viewer-body">
				<!-- No {#key} here: remounting per gallery step destroys the
					FileViewer DOM (and with it the fullscreen element). FileViewer
					reloads reactively on entryId instead. -->
				<FileViewer entryId={active.entry.id} />
			</div>
		</div>
	</div>
{/if}

<style>
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

	.viewer-actions {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		flex-shrink: 0;
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
</style>
