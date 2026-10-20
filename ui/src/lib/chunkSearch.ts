// Page-local AWMF chunk search state + actions for the /leitlinien route.
// Deliberately NOT wired into stores/search.ts (entry search stays isolated).
import { chunkSearchApi, ragApi, type ChunkResultItem, type RagSourceItem } from './api.js';

const HISTORY_KEY = 'medwiss_leitlinien_history';
const MAX_HISTORY = 10;
const RESULTS_PER_PAGE = 20;

export interface ChunkQuery {
	query: string;
	page: number; // 1-indexed
	results: ChunkResultItem[];
	isLoading: boolean;
	error: string | null;
	total: number;
	totalPages: number;
}

export function initialChunkQuery(): ChunkQuery {
	return {
		query: '',
		page: 1,
		results: [],
		isLoading: false,
		error: null,
		total: 0,
		totalPages: 0,
	};
}

export async function searchChunks(state: ChunkQuery, q?: string): Promise<ChunkQuery> {
	const query = (q ?? state.query).trim();
	if (!query) return { ...state, results: [], total: 0, totalPages: 0, error: null };

	const next: ChunkQuery = { ...state, query, isLoading: true, error: null };
	try {
		const resp = await chunkSearchApi.search(query, {
			limit: RESULTS_PER_PAGE,
			offset: (state.page - 1) * RESULTS_PER_PAGE,
		});
		const totalPages = Math.ceil(resp.total / RESULTS_PER_PAGE);
		return {
			...next,
			isLoading: false,
			results: resp.items,
			total: resp.total,
			totalPages,
		};
	} catch (e) {
		const msg = e instanceof Error ? e.message : 'Suche fehlgeschlagen';
		return { ...next, isLoading: false, error: msg };
	}
}

export interface RagQuery {
	query: string;
	answer: string;
	sources: RagSourceItem[];
	isLoading: boolean;
	error: string | null;
}

export function initialRagQuery(): RagQuery {
	return {
		query: '',
		answer: '',
		sources: [],
		isLoading: false,
		error: null,
	};
}

export async function answerRag(state: RagQuery, q?: string): Promise<RagQuery> {
	const query = (q ?? state.query).trim();
	if (!query) return { ...state, query, answer: '', sources: [], error: null };

	const next: RagQuery = { ...state, query, isLoading: true, error: null };
	try {
		const resp = await ragApi.answer(query);
		return {
			...next,
			isLoading: false,
			answer: resp.answer,
			sources: resp.sources,
		};
	} catch (e) {
		const msg = e instanceof Error ? e.message : 'Antwort fehlgeschlagen';
		return { ...next, isLoading: false, error: msg };
	}
}

export function loadHistory(): string[] {
	try {
		const raw = localStorage.getItem(HISTORY_KEY);
		return raw ? (JSON.parse(raw) as string[]) : [];
	} catch {
		return [];
	}
}

export function pushHistory(query: string): string[] {
	const items = [query, ...loadHistory().filter((q) => q !== query)].slice(0, MAX_HISTORY);
	try {
		localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
	} catch {
		// ignore storage failures
	}
	return items;
}

export function clearHistory(): void {
	try {
		localStorage.removeItem(HISTORY_KEY);
	} catch {
		// ignore storage failures
	}
}
