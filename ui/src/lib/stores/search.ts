import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

// Types
export interface SearchResult {
	id: number;
	title: string;
	content: string;
	category: string;
	summary: string;
	score: number;
	fachgebiete: string[];
	diagnosen: string[];
	symptome: string[];
	created_at: string;
	updated_at: string;
	source_path: string | null;
}

export interface SearchState {
	query: string;
	results: SearchResult[];
	isLoading: boolean;
	error: string | null;
	currentPage: number;
	totalPages: number;
	totalResults: number;
	filters: SearchFilters;
	filterOptions: FilterOptions;
}

export interface SearchFilters {
	fachgebiet: string;
	diagnose: string;
	symptom: string;
	dokumenttyp: string;
	ordner_label: string;
	folder: string;
}

export interface FilterOption {
	id: number;
	name: string;
	count: number;
}

export interface FilterOptions {
	fachgebiete: FilterOption[];
	diagnosen: FilterOption[];
	symptome: FilterOption[];
	dokumenttypen: FilterOption[];
	ordner_labels: FilterOption[];
	folders: { name: string; count: number }[];
}

export const emptyFilters: SearchFilters = {
	fachgebiet: '',
	diagnose: '',
	symptom: '',
	dokumenttyp: '',
	ordner_label: '',
	folder: ''
};


export interface SearchHistoryItem {
	query: string;
	timestamp: number;
}

// Constants
const RESULTS_PER_PAGE = 10;
const HISTORY_KEY = 'medwiss_search_history';
const MAX_HISTORY_ITEMS = 10;

const initialState: SearchState = {
	query: '',
	results: [],
	isLoading: false,
	error: null,
	currentPage: 1,
	totalPages: 0,
	totalResults: 0,
	filters: { ...emptyFilters },
	filterOptions: {
		fachgebiete: [],
		diagnosen: [],
		symptome: [],
		dokumenttypen: [],
		ordner_labels: [],
		folders: []
	}
};

// Create stores
function createSearchStore() {
	const { subscribe, set, update } = writable<SearchState>(initialState);

	return {
		subscribe,
		set,
		update,

		// Actions
		setQuery: (query: string) => {
			update(state => ({ ...state, query }));
		},

		setPage: (page: number) => {
			update(state => ({ ...state, currentPage: page }));
		},

		setFilter: (name: keyof SearchFilters, value: string) => {
			update(state => ({
				...state,
				filters: { ...state.filters, [name]: value },
				currentPage: 1
			}));
		},

		clearFilters: () => {
			update(state => ({ ...state, filters: { ...emptyFilters }, currentPage: 1 }));
		},

		setFilterOptions: (options: FilterOptions) => {
			update(state => ({ ...state, filterOptions: options }));
		},

		setLoading: (isLoading: boolean) => {
			update(state => ({ ...state, isLoading }));
		},

		setError: (error: string | null) => {
			update(state => ({ ...state, error }));
		},

		setResults: (results: SearchResult[], totalResults: number) => {
			update(state => ({
				...state,
				results,
				totalResults,
				totalPages: Math.ceil(totalResults / RESULTS_PER_PAGE),
				isLoading: false,
				error: null
			}));
		},

		reset: () => {
			set(initialState);
		}
	};
}

// Search history store
function createSearchHistoryStore() {
	const { subscribe, set, update } = writable<SearchHistoryItem[]>([]);

	// Load from localStorage on init
	if (browser) {
		try {
			const saved = localStorage.getItem(HISTORY_KEY);
			if (saved) {
				set(JSON.parse(saved));
			}
		} catch (e) {
			console.error('Failed to load search history:', e);
		}
	}

	return {
		subscribe,

		add: (query: string) => {
			if (!query.trim()) return;

			update(history => {
				const newItem: SearchHistoryItem = {
					query: query.trim(),
					timestamp: Date.now()
				};

				// Remove duplicates and add to front
				const filtered = history.filter(
					h => h.query.toLowerCase() !== query.toLowerCase()
				);
				const newHistory = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);

				// Save to localStorage
				if (browser) {
					try {
						localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
					} catch (e) {
						console.error('Failed to save search history:', e);
					}
				}

				return newHistory;
			});
		},

		clear: () => {
			set([]);
			if (browser) {
				try {
					localStorage.removeItem(HISTORY_KEY);
				} catch (e) {
					console.error('Failed to clear search history:', e);
				}
			}
		},

		remove: (query: string) => {
			update(history => {
				const newHistory = history.filter(
					h => h.query.toLowerCase() !== query.toLowerCase()
				);

				if (browser) {
					try {
						localStorage.setItem(HISTORY_KEY, JSON.stringify(newHistory));
					} catch (e) {
						console.error('Failed to save search history:', e);
					}
				}

				return newHistory;
			});
		}
	};
}

// Raw API shapes (unvalidated JSON from fetch)
interface RawLabel {
	name?: string;
}

interface RawEntry {
	id: number;
	titel: string;
	inhalt?: string | null;
	dokumenttyp?: string | null;
	unterkategorie?: string | null;
	zusammenfassung?: string | null;
	rank?: number;
	fachgebiete?: (string | RawLabel)[] | null;
	diagnosen?: (string | RawLabel)[] | null;
	symptome?: (string | RawLabel)[] | null;
	created_at?: string;
	updated_at?: string;
	source_path?: string | null;
}

interface RawListResponse {
	items?: RawEntry[];
	total?: number;
}

function labelName(value: string | RawLabel): string {
	return typeof value === 'string' ? value : (value.name ?? '');
}

function mapEntryToSearchResult(entry: RawEntry): SearchResult {
	return {
		id: entry.id,
		title: entry.titel,
		content: entry.inhalt ?? '',
		category: entry.dokumenttyp ?? entry.unterkategorie ?? 'Allgemein',
		summary: entry.zusammenfassung ?? '',
		score: entry.rank ?? 0,
		fachgebiete: (entry.fachgebiete ?? []).map(labelName),
		diagnosen: (entry.diagnosen ?? []).map(labelName),
		symptome: (entry.symptome ?? []).map(labelName),
		created_at: entry.created_at ?? '',
		updated_at: entry.updated_at ?? '',
		source_path: entry.source_path ?? null
	};
}

let searchGeneration = 0;

// Execute search - empty query lists entries, otherwise keyword search.
// Active filters route through /search either way (q is optional there).
export async function executeSearch() {
	const gen = ++searchGeneration;
	const state = get(searchStore);

	searchStore.setLoading(true);
	searchStore.setError(null);

	try {
		const params = new URLSearchParams();
		params.append('limit', RESULTS_PER_PAGE.toString());
		params.append('offset', ((state.currentPage - 1) * RESULTS_PER_PAGE).toString());

		const { fachgebiet, diagnose, symptom, dokumenttyp, ordner_label, folder } =
			state.filters;
		const hasFilters = Boolean(
			fachgebiet || diagnose || symptom || dokumenttyp || ordner_label || folder
		);
		if (fachgebiet) params.append('fachgebiet', fachgebiet);
		if (diagnose) params.append('diagnose', diagnose);
		if (symptom) params.append('symptom', symptom);
		if (dokumenttyp) params.append('dokumenttyp', dokumenttyp);
		if (ordner_label) params.append('ordner_label', ordner_label);
		if (folder) params.append('folder', folder);

		let data: { items: SearchResult[]; total: number };

		if (!state.query.trim() && !hasFilters) {
			const response = await fetch(`/api/v1/entries?${params.toString()}`);

			if (!response.ok) {
				throw new Error(`Failed to load entries: ${response.statusText}`);
			}

			const entriesData: RawListResponse = await response.json();
			data = {
				items: (entriesData.items ?? []).map(mapEntryToSearchResult),
				total: entriesData.total ?? 0
			};
		} else {
			params.append('q', state.query.trim());

			const response = await fetch(`/api/v1/search?${params.toString()}`);

			if (!response.ok) {
				throw new Error(`Search failed: ${response.statusText}`);
			}

			const searchData = await response.json();
			data = {
				items: (searchData.items ?? []).map(mapEntryToSearchResult),
				total: searchData.total ?? 0
			};

			if (searchData.filters) {
				searchStore.setFilterOptions(searchData.filters);
			}

			if (state.query.trim()) {
				searchHistory.add(state.query);
			}
		}

		if (gen !== searchGeneration) return;
		searchStore.setResults(data.items, data.total);
	} catch (error) {
		if (gen !== searchGeneration) return;
		searchStore.setError(error instanceof Error ? error.message : 'Unknown error');
		searchStore.setResults([], 0);
	}
}

/** Load facet option lists (independent of the current result set). */
export async function loadFilterOptions() {
	try {
		const response = await fetch('/api/v1/search?limit=1');
		if (!response.ok) return;
		const searchData = await response.json();
		if (searchData.filters) {
			searchStore.setFilterOptions(searchData.filters);
		}
	} catch {
		// Facets stay empty; search still works.
	}
}

// Export store instances
export const searchStore = createSearchStore();
export const searchHistory = createSearchHistoryStore();
