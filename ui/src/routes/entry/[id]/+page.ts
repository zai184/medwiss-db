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
	return { entry };
};

// Dynamic per-entry route — excluded from static prerendering.
export const prerender = false;
