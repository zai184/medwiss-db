// Mermaid rendering for markdown content.
// The markdown pipeline (marked + DOMPurify) keeps ```mermaid fences as
// <pre><code class="language-mermaid">…</code></pre>. renderMermaid swaps
// those for inline SVGs.

import mermaid from 'mermaid';

let initialized = false;

function ensureInit() {
	if (initialized) return;
	mermaid.initialize({
		startOnLoad: false,
		theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
		securityLevel: 'strict'
	});
	initialized = true;
}

/** Render all ```mermaid fences inside `root`. Idempotent per block; blocks
 *  that fail to parse keep showing their source. */
export async function renderMermaid(root: HTMLElement): Promise<void> {
	const codes = Array.from(root.querySelectorAll('pre > code.language-mermaid'));
	if (!codes.length) return;
	ensureInit();
	for (const code of codes) {
		const pre = code.parentElement as HTMLElement;
		if (pre.dataset.mermaidDone) continue;
		pre.dataset.mermaidDone = '1';
		const source = code.textContent ?? '';
		try {
			const id = `mmd-${Math.random().toString(36).slice(2)}`;
			const { svg } = await mermaid.render(id, source);
			// mermaid.render returns generated SVG, not user HTML — safe to inject.
			pre.innerHTML = svg;
			pre.className = 'mermaid-diagram';
		} catch {
			// keep the fenced source visible on parse errors
		}
	}
}
