import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const response = await fetch(`/api/v1/entries/${params.id}`);

	if (!response.ok) {
		if (response.status === 404) {
			throw error(404, 'Eintrag nicht gefunden');
		}
		throw error(response.status, 'Fehler beim Laden des Eintrags');
	}

	const entry = await response.json();

	const [fachResponse, diagResponse, sympResponse, tagSuggestionsResponse, typResponse, labelResponse] =
		await Promise.all([
			fetch('/api/v1/fachgebiete?reviewed_only=true').then((r) => r.json()),
			fetch('/api/v1/diagnosen').then((r) => r.json()),
			fetch('/api/v1/symptome').then((r) => r.json()),
			fetch(`/api/v1/entries/${params.id}/tag-suggestions`).then(async (r) =>
				r.ok ? r.json() : null
			),
			fetch('/api/v1/dokumenttypen').then((r) => r.json()),
			fetch('/api/v1/ordner-labels').then((r) => r.json())
		]);
	// Include this entry's linked tags even if auto-created (not in curated list)
	const fachById = new Map<number, (typeof entry.fachgebiete)[number]>();
	for (const f of fachResponse) fachById.set(f.id, f);
	for (const f of entry.fachgebiete) fachById.set(f.id, f);
	const fachgebiete = [...fachById.values()].sort((a, b) => a.name.localeCompare(b.name, 'de'));

	const typById = new Map<number, { id: number; name: string }>();
	for (const t of typResponse) typById.set(t.id, t);
	if (entry.dokumenttyp_ref) typById.set(entry.dokumenttyp_ref.id, entry.dokumenttyp_ref);
	const dokumenttypen = [...typById.values()].sort((a, b) => a.name.localeCompare(b.name, 'de'));

	const labelById = new Map<number, { id: number; name: string }>();
	for (const l of labelResponse) labelById.set(l.id, l);
	for (const l of entry.ordner_labels) labelById.set(l.id, l);
	const ordnerLabels = [...labelById.values()].sort((a, b) => a.name.localeCompare(b.name, 'de'));

	return {
		entry,
		fachgebiete,
		diagnosen: diagResponse,
		symptome: sympResponse,
		dokumenttypen: typResponse,
		ordnerLabels: labelResponse,
		tagSuggestions: tagSuggestionsResponse
	};
};

// Dynamic per-entry route — excluded from static prerendering.
export const prerender = false;
