import { writable } from 'svelte/store';
import { goto } from '$app/navigation';

export interface ViewerEntry {
	id: number;
	title: string;
}

/** Entry metadata a browse surface has in hand when a row is clicked. */
export interface ClickableEntry extends ViewerEntry {
	source_path?: string | null;
}

interface ViewerState {
	entry: ViewerEntry;
	/** Swipeable gallery: file-backed entries of the list clicked from. */
	gallery: ViewerEntry[];
	index: number;
}

function createEntryViewer() {
	const { subscribe, set, update } = writable<ViewerState | null>(null);
	return {
		subscribe,
		open: (entry: ViewerEntry, gallery: ViewerEntry[] = [entry]) => {
			const index = Math.max(0, gallery.findIndex((g) => g.id === entry.id));
			set({ entry: gallery[index] ?? entry, gallery, index });
		},
		close: () => set(null),
		next: () => update((s) => (s && s.index < s.gallery.length - 1 ? { ...s, index: s.index + 1, entry: s.gallery[s.index + 1] } : s)),
		prev: () => update((s) => (s && s.index > 0 ? { ...s, index: s.index - 1, entry: s.gallery[s.index - 1] } : s))
	};
}

export const entryViewer = createEntryViewer();

/**
 * Browse-surface click handler: file-backed entries open the in-app fullscreen
 * viewer overlay (rendered once in the root layout); file-less entries keep
 * navigating to their item page. `list` (the browse list the entry came from,
 * same shape) turns the viewer into a swipeable gallery of its file-backed
 * entries.
 */
export function openBrowseEntry(entry: ClickableEntry, list?: ClickableEntry[]) {
	if (entry.source_path) {
		const gallery = (list ?? [entry]).filter((e) => e.source_path);
		entryViewer.open({ id: entry.id, title: entry.title }, gallery);
	} else {
		goto(`/entry/${entry.id}`);
	}
}
