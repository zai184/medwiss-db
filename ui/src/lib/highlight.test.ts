import { describe, expect, test } from 'bun:test';
import { escapeHtml } from './escape.js';
import { highlightTerms } from './highlight.js';

describe('escapeHtml', () => {
	test('escapes all HTML metacharacters', () => {
		expect(escapeHtml('<img src=x onerror=alert(1)> & "q" \'')).toBe(
			'&lt;img src=x onerror=alert(1)&gt; &amp; &quot;q&quot; &#39;'
		);
	});
});

describe('highlightTerms (XSS regression: audit 2026-09-24 High)', () => {
	test('escapes payload even with empty query', () => {
		expect(highlightTerms('<img src=x onerror=alert(1)>', '', 'm')).toBe(
			'&lt;img src=x onerror=alert(1)&gt;'
		);
	});

	test('escapes payload when a term matches', () => {
		const out = highlightTerms('<b>Herz</b> failure', 'herz', 'm');
		expect(out).toBe('&lt;b&gt;<mark class="m">Herz</mark>&lt;/b&gt; failure');
	});

	test('regex metacharacters in query do not break matching', () => {
		expect(highlightTerms('a(bc)d', '(bc', 'm')).toBe('a<mark class="m">(bc</mark>)d');
	});

	test('short terms are not highlighted', () => {
		expect(highlightTerms('ab cd', 'ab', 'm')).toBe('ab cd');
	});
});
