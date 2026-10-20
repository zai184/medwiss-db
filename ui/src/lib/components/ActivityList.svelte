<script lang="ts">
  import { FileText, Clock, ArrowRight } from 'lucide-svelte';
  import type { EntryResponse } from '$lib/api';
  import { openBrowseEntry } from '$lib/stores/entryViewer.js';
  
  interface Props {
    entries: EntryResponse[];
    maxItems?: number;
  }

  let { entries, maxItems = 5 }: Props = $props();
  const displayEntries = $derived(entries.slice(0, maxItems));

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(date);
  }

  function getCategoryColor(category: string | null): string {
    const colors: Record<string, string> = {
      'lehrfall': 'bg-blue-100 text-blue-700',
      'richtlinien': 'bg-green-100 text-green-700',
      'forschung': 'bg-purple-100 text-purple-700',
      'SOPs': 'bg-amber-100 text-amber-700',
      'Leitlinien': 'bg-emerald-100 text-emerald-700',
      'Studien': 'bg-violet-100 text-violet-700'
    };
    return colors[category || ''] || 'bg-gray-100 text-gray-700';
  }

  function truncateText(text: string | null, maxLength: number = 60): string {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }


  function handleOpen(entry: EntryResponse) {
    const clickable = (list: EntryResponse[]) => list.map((e) => ({ id: e.id, title: e.titel, source_path: e.source_path }));
    openBrowseEntry(clickable([entry])[0], clickable(entries));
  }
</script>

<div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
  <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
    <div class="flex items-center gap-2">
      <Clock class="w-5 h-5 text-gray-500" />
      <h3 class="text-lg font-semibold text-gray-900">Letzte Aktivitäten</h3>
    </div>
    <span class="text-sm text-gray-500">{entries.length} Einträge gesamt</span>
  </div>
  
  <div class="divide-y divide-gray-100">
    {#if displayEntries.length === 0}
      <div class="px-6 py-8 text-center text-gray-500">
        <FileText class="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <p>Keine Einträge vorhanden</p>
      </div>
    {:else}
      {#each displayEntries as entry (entry.id)}
        <a
          href="/entry/{entry.id}"
          onclick={(e) => {
            e.preventDefault();
            handleOpen(entry);
          }}
          class="block px-6 py-4 hover:bg-gray-50 transition-colors group"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <h4 class="font-medium text-gray-900 truncate group-hover:text-blue-600 transition-colors">
                  {entry.titel}
                </h4>
                {#if entry.dokumenttyp}
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {getCategoryColor(entry.dokumenttyp)}">
                    {entry.dokumenttyp}
                  </span>
                {/if}
              </div>
              {#if entry.zusammenfassung}
                <p class="text-sm text-gray-500 truncate">
                  {truncateText(entry.zusammenfassung)}
                </p>
              {/if}
              <div class="flex items-center gap-4 mt-2 text-xs text-gray-400">
                <span>{formatDate(entry.created_at)}</span>
                {#if entry.fachgebiete.length > 0}
                  <span class="text-gray-300">•</span>
                  <span class="truncate">{entry.fachgebiete.map(f => f.name).join(', ')}</span>
                {/if}
              </div>
            </div>
            <ArrowRight class="w-5 h-5 text-gray-300 group-hover:text-blue-500 transition-colors flex-shrink-0" />
          </div>
        </a>
      {/each}
    {/if}
  </div>
  
  {#if entries.length > maxItems}
    <div class="px-6 py-3 border-t border-gray-100 bg-gray-50">
      <a href="/search" class="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center justify-center gap-1">
        Alle anzeigen
        <ArrowRight class="w-4 h-4" />
      </a>
    </div>
  {/if}
</div>
