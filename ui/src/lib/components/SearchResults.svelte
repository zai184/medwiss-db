<script lang="ts">
	import { FileText, Calendar, Tag, ChevronLeft, ChevronRight, AlertCircle, File } from 'lucide-svelte';
	import { searchStore, executeSearch } from '$lib/stores/search.js';
	import type { SearchResult } from '$lib/stores/search.js';
	import { openBrowseEntry } from '$lib/stores/entryViewer.js';
	import { highlightTerms } from '$lib/highlight.js';
	
	function openEntry(result: SearchResult) {
		openBrowseEntry(result, $searchStore.results);
	}
	
	// Highlight search terms in text (escaped — see $lib/highlight.ts)
	function highlightText(text: string, query: string): string {
		return highlightTerms(text, query, 'search-highlight');
	}
	
	
	// Format date
	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString('de-DE', {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric'
		});
	}
	
	// Truncate text
	function truncate(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.substring(0, maxLength).trim() + '...';
	}
	
	// Handle page change
	function goToPage(page: number) {
		if (page >= 1 && page <= $searchStore.totalPages) {
			searchStore.setPage(page);
			executeSearch();
			// Scroll to top of results
			window.scrollTo({ top: 0, behavior: 'smooth' });
		}
	}
	
	// Generate page numbers for pagination
	function getPageNumbers(current: number, total: number): (number | string)[] {
		const pages: (number | string)[] = [];
		
		if (total <= 7) {
			for (let i = 1; i <= total; i++) {
				pages.push(i);
			}
		} else {
			if (current <= 3) {
				pages.push(1, 2, 3, 4, '...', total);
			} else if (current >= total - 2) {
				pages.push(1, '...', total - 3, total - 2, total - 1, total);
			} else {
				pages.push(1, '...', current - 1, current, current + 1, '...', total);
			}
		}
		
		return pages;
	}
	
	// Get category color
	function getCategoryColor(category: string): string {
		const colors: Record<string, string> = {
			'SOPs': '#2563eb',
			'Leitlinien': '#059669',
			'Studien': '#7c3aed',
			'Red Flags': '#dc2626',
			'Fragebögen': '#d97706',
			'Infoblätter': '#0891b2',
			'Fälle': '#be185d',
			'Fortbildung': '#4338ca'
		};
		return colors[category] || '#6b7280';
	}
</script>

<div class="search-results">
	{#if $searchStore.isLoading}
		<div class="loading-state">
			<div class="spinner"></div>
			<span>Suche läuft...</span>
		</div>
	{:else if $searchStore.error}
		<div class="error-state">
			<AlertCircle size={24} />
			<p>{$searchStore.error}</p>
		</div>
	{:else if $searchStore.results.length === 0}
		{#if $searchStore.query}
			<div class="empty-state">
				<FileText size={48} />
				<p>Keine Ergebnisse gefunden für "{$searchStore.query}"</p>
				<span class="empty-hint">Versuchen Sie andere Suchbegriffe oder Filter</span>
			</div>
		{:else}
			<div class="empty-state">
				<FileText size={48} />
				<p>Keine Einträge vorhanden</p>
				<span class="empty-hint">Fügen Sie neue Einträge über "Neuer Eintrag" hinzu</span>
			</div>
		{/if}
	{:else}
		<div class="results-header">
			<span class="results-count">
				{#if $searchStore.query}
					{$searchStore.totalResults} Ergebnis{$searchStore.totalResults !== 1 ? 'se' : ''}
					für "<strong>{$searchStore.query}</strong>"
				{:else}
					{$searchStore.totalResults} Eintrag{$searchStore.totalResults !== 1 ? 'e' : ''} insgesamt
				{/if}
			</span>
		</div>
		
		<div class="results-list">
			{#each $searchStore.results as result (result.id)}
            <div class="result-card" onclick={() => openEntry(result)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && openEntry(result)}>
					<div class="result-header">
						<div class="result-meta">
							<span 
								class="result-category"
								style="background-color: {getCategoryColor(result.category)}20; color: {getCategoryColor(result.category)}"
							>
								{result.category}
							</span>
							<span class="result-date">
								<Calendar size={14} />
								{formatDate(result.created_at)}
							</span>
							{#if result.source_path}
								<span class="result-file-indicator" title="Originaldatei verfügbar">
									<File size={14} />
									Datei
								</span>
							{/if}
						</div>
					</div>
					
					<h3 class="result-title">
						{@html highlightText(result.title, $searchStore.query)}
					</h3>
					
					<p class="result-summary">
						{@html highlightText(truncate(result.summary || result.content, 200), $searchStore.query)}
					</p>
					
					{#if result.fachgebiete.length > 0 || result.diagnosen.length > 0 || result.symptome.length > 0}
						<div class="result-tags">
							{#each result.fachgebiete as fach}
								<span class="tag tag-fach">
									<Tag size={12} />
									{fach}
								</span>
							{/each}
							{#each result.diagnosen.slice(0, 2) as diagnose}
								<span class="tag tag-diagnose">{diagnose}</span>
							{/each}
							{#each result.symptome.slice(0, 2) as symptom}
								<span class="tag tag-symptom">{symptom}</span>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
		
		{#if $searchStore.totalPages > 1}
			<div class="pagination">
				<button 
					class="page-btn"
					disabled={$searchStore.currentPage === 1}
					onclick={() => goToPage($searchStore.currentPage - 1)}
				>
					<ChevronLeft size={18} />
				</button>
				
				{#each getPageNumbers($searchStore.currentPage, $searchStore.totalPages) as page}
					{#if page === '...'}
						<span class="page-ellipsis">...</span>
					{:else}
						<button 
							class="page-btn"
							class:active={page === $searchStore.currentPage}
							onclick={() => goToPage(page as number)}
						>
							{page}
						</button>
					{/if}
				{/each}
				
				<button 
					class="page-btn"
					disabled={$searchStore.currentPage === $searchStore.totalPages}
					onclick={() => goToPage($searchStore.currentPage + 1)}
				>
					<ChevronRight size={18} />
				</button>
			</div>
		{/if}
	{/if}
</div>

<style>
	.search-results {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-4);
		color: var(--color-text-secondary);
	}
	
	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid var(--color-border);
		border-top-color: var(--color-primary);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}
	
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-3);
		color: var(--color-error);
		text-align: center;
	}
	
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-4);
		color: var(--color-text-secondary);
		text-align: center;
	}
	
	.empty-hint {
		font-size: var(--font-size-sm);
		color: var(--color-text-tertiary);
	}
	
	.results-header {
		padding-bottom: var(--space-3);
		border-bottom: 1px solid var(--color-border);
	}
	
	.results-count {
		font-size: var(--font-size-sm);
		color: var(--color-text-secondary);
	}
	
	.results-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}
	
	.result-card {
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		padding: var(--space-5);
		transition: box-shadow var(--transition-fast), border-color var(--transition-fast);
		cursor: pointer;
	}
	
	.result-card:hover {
		box-shadow: var(--shadow-md);
		border-color: var(--color-border-hover);
	}
	
	.result-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: var(--space-3);
		gap: var(--space-3);
	}
	
	.result-meta {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}
	
	.result-category {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-semibold);
		padding: 4px 10px;
		border-radius: var(--radius-full);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}
	
	.result-date {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-size-xs);
		color: var(--color-text-tertiary);
	}
	
	.result-file-indicator {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-size-xs);
		color: var(--color-primary);
		font-weight: var(--font-weight-medium);
	}
	
	
	.result-title {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		margin-bottom: var(--space-2);
		line-height: var(--line-height-tight);
	}
	
	.result-title :global(.search-highlight) {
		background: var(--color-warning-subtle);
		color: var(--color-warning);
		padding: 0 2px;
		border-radius: 2px;
	}
	
	.result-summary {
		font-size: var(--font-size-sm);
		color: var(--color-text-secondary);
		line-height: var(--line-height-relaxed);
		margin-bottom: var(--space-3);
	}
	
	.result-summary :global(.search-highlight) {
		background: var(--color-warning-subtle);
		color: var(--color-warning);
		font-weight: var(--font-weight-medium);
		padding: 0 2px;
		border-radius: 2px;
	}
	
	.result-tags {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}
	
	.tag {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: var(--font-size-xs);
		padding: 4px 10px;
		border-radius: var(--radius-md);
		background: var(--color-background-tertiary);
		color: var(--color-text-secondary);
	}
	
	.tag-fach {
		background: var(--color-primary-subtle);
		color: var(--color-primary-dark);
	}
	
	.tag-diagnose {
		background: var(--color-accent-subtle);
		color: var(--color-accent);
	}
	
	.tag-symptom {
		background: var(--color-secondary-subtle);
		color: var(--color-secondary-dark);
	}
	
	.pagination {
		display: flex;
		justify-content: center;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-1);
		padding-top: var(--space-6);
		border-top: 1px solid var(--color-border);
	}
	
	.page-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 36px;
		height: 36px;
		padding: 0 var(--space-2);
		border: 1px solid var(--color-border);
		background: var(--color-background-primary);
		color: var(--color-text-secondary);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}
	
	.page-btn:hover:not(:disabled) {
		background: var(--color-background-tertiary);
		border-color: var(--color-border-hover);
	}
	
	.page-btn.active {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: white;
	}
	
	.page-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	
	.page-ellipsis {
		color: var(--color-text-tertiary);
		padding: 0 var(--space-1);
	}
</style>
