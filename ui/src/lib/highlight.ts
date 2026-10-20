import { escapeHtml } from './escape.js';

/**
 * Escape DB-derived text, then wrap search-term matches in a <mark>.
 * XSS invariant: no unescaped input ever reaches the raw-HTML sink.
 */
export function highlightTerms(text: string, query: string, markClass: string): string {
	const safe = escapeHtml(text);
	const terms = query
		.trim()
		.split(/\s+/)
		.filter((t) => t.length > 2)
		.map((t) => escapeHtml(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
	if (terms.length === 0) return safe;
	const re = new RegExp(`(${terms.join('|')})`, 'gi');
	return safe.replace(re, `<mark class="${markClass}">$1</mark>`);
}
