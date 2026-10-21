import type { EntryResponse } from '$lib/api';

/**
 * Themed grouping for the Notfall item lists.
 *
 * Pure view-layer transform: a curated, keyword-driven mapping from a corpus
 * entry's titel to a German section heading. Matching is substring-based on a
 * lower-cased, umlaut-folded copy of the title. Rules are checked in the order
 * they are declared (most specific first — e.g. paediatric reanimation before
 * the broad reanimation rules), so an entry lands in the first matching group.
 * New corpus files that hit no rule still surface under the tab's fallback
 * heading ("Sonstiges" / "Weitere") — nothing is ever silently dropped.
 *
 * Since 2026-10-21 the 'algos' tab is gone: the md quick-reference docs share
 * the 'files' tab and are grouped by the same rules.
 */
export interface GroupRule {
	heading: string;
	keywords: string[];
}

interface TabGroups {
	/** Match order: first rule whose keyword hits wins (most specific first). */
	rules: GroupRule[];
	/** Display order of headings (must include every rule heading). */
	order: string[];
	/** Heading for entries that match no rule; always shown last when non-empty. */
	fallback: string;
}

export const NOTFALL_GROUPS: Record<string, TabGroups> = {
	// 'files' = label "SOPs" — non-md resuscitation media (GRC/ARC/ERC algorithms, leaflets, figures)
	files: {
		rules: [
			{
				heading: 'Kinder & Neugeborene',
				keywords: [
					'nls',
					'pls',
					'epals',
					'pals',
					'paediatric',
					'neonatal',
					'erstebeurteilungneugeborenen',
				],
			},
			{
				heading: 'Kardiologie & Nachsorge',
				keywords: [
					'coronary',
					'koronarthrombose',
					'post resus',
					'post resuscitation',
					'postreanimation',
					'catheter',
					'katheterlabor',
					'cardiac surgery',
					'herzoperation',
					'organ donation',
					'follow up',
					'nachsorge',
				],
			},
			{
				heading: 'Spezielle Situationen & Umwelt',
				keywords: [
					'trauma',
					'special circumstances',
					'opioid',
					'drowing',
					'ertrinken',
					'hitzeschlag',
					'hypertherm',
					'hypotherm',
					'fremdkorper',
					'abcde',
					'xabcde',
					'ample',
					'anaphylax',
				],
			},
			{
				heading: 'Rhythmusstörungen & Elektrolyte',
				keywords: ['tachy', 'tachykardie', 'brady', 'bradykardie', 'kalaemia', 'kaliamie'],
			},
			{
				heading: 'Reanimation & Kreislaufstillstand',
				keywords: [
					'bls',
					'basic life',
					'als',
					'kreislauf',
					'reanimation',
					'chain of survival',
					'uberlebenskette',
					'ueberlebenskette',
					'reversible',
					'3 steps',
					'3schritte',
					'step by step',
					'first aid',
					'in hospital',
					'ssl key',
					'advanced life support',
				],
			},
			{
				heading: 'Neurologie & Schlaganfall',
				keywords: ['be fast', 'fast', 'gcs', 'schwindel', 'insult'],
			},
			{
				heading: 'Hintergrund & Schulung',
				keywords: [
					'epidemiology',
					'education',
					'ethics',
					'ethical',
					'ethische',
					'utstein',
					'systems saving',
					'key messages',
					'leaflet',
					'gl2025',
					'pocketcard',
					'ssl',
				],
			},
		],
		order: [
			'Reanimation & Kreislaufstillstand',
			'Rhythmusstörungen & Elektrolyte',
			'Kinder & Neugeborene',
			'Kardiologie & Nachsorge',
			'Spezielle Situationen & Umwelt',
			'Neurologie & Schlaganfall',
			'Hintergrund & Schulung',
		],
		fallback: 'Weitere',
	},
	// 'sops' = label "SOPs Notaufnahme" — clinical emergency SOPs
	sops: {
		rules: [
			{
				heading: 'Kardiologie & Kreislauf',
				keywords: [
					'herz',
					'vorhofflimmern',
					'infarkt',
					'synkope',
					'thoraxschmerz',
					'stillstand',
					'hypertensiver',
					'schock',
					'herzinsuffizienz',
				],
			},
			{
				heading: 'Gefäße & Hämostase',
				keywords: ['aorten', 'embolie', 'venenthrombose', 'heparin'],
			},
			{
				heading: 'Lunge & Atemwege',
				keywords: ['copd', 'asthma', 'dyspnoe', 'pneumonie', 'pleuraerguss'],
			},
			{
				heading: 'Gastro & Abdomen',
				keywords: [
					'divertikulitis',
					'gastroenteritis',
					'mesenterial',
					'pankreatitis',
					'bauchschmerz',
					'hyperemesis',
					'erbrechen',
					'fremdkoerperingestion',
					'ikterus',
					'gastrointestinale',
					'peritonitis',
				],
			},
			{
				heading: 'Niere, Elektrolyte & Stoffwechsel',
				keywords: [
					'nierensch',
					'nebennieren',
					'ketoazidose',
					'hyperosmol',
					'hypoglykaem',
					'myxoedem',
					'natr',
					'nierenkolik',
					'rhabdomyolyse',
					'harnverhalt',
					'gicht',
				],
			},
			{
				heading: 'Infektion & Sepsis',
				keywords: ['sepsis', 'fieber', 'harnwegsinfektion', 'erysipel', 'tonsillitis'],
			},
			{
				heading: 'Neurologie & Psychiatrie',
				keywords: [
					'kopfschmerz',
					'epilepticus',
					'meningitis',
					'delir',
					'vigilanz',
					'amnesie',
					'bewusstseinsverlust',
					'zerebrale venen',
					'enzephalopathie',
				],
			},
			{
				heading: 'Hämatologie & Onkologie',
				keywords: [
					'anaemie',
					'thrombozytopenie',
					'ttp',
					'tumorlyse',
					'vena cava',
					'zerebrale metastasen',
				],
			},
			{
				heading: 'Intoxikation & Umwelt',
				keywords: ['intoxikation', 'alkohol', 'kohlenmonoxid', 'hitzschlag', 'strom'],
			},
			{
				heading: 'Allergie & Immunologie',
				keywords: ['anaphylaxie'],
			},
		],
		order: [
			'Kardiologie & Kreislauf',
			'Gefäße & Hämostase',
			'Lunge & Atemwege',
			'Gastro & Abdomen',
			'Niere, Elektrolyte & Stoffwechsel',
			'Infektion & Sepsis',
			'Neurologie & Psychiatrie',
			'Hämatologie & Onkologie',
			'Intoxikation & Umwelt',
			'Allergie & Immunologie',
		],
		fallback: 'Sonstiges',
	},
};

/** Fold case + umlauts so matching is robust against ae/oe/ue spellings. */
function fold(s: string): string {
	return s
		.toLowerCase()
		.replace(/ä/g, 'ae')
		.replace(/ö/g, 'oe')
		.replace(/ü/g, 'ue')
		.replace(/ß/g, 'ss');
}

export interface EntryGroup {
	heading: string;
	items: EntryResponse[];
}

/**
 * Assign entries to themed groups. Match order follows the declared rules;
 * output follows the tab's display `order`. Entries matching no rule land in
 * the tab's fallback heading, which is appended last (when non-empty).
 */
export function groupEntries(tabId: string, items: EntryResponse[]): EntryGroup[] {
	const tab = NOTFALL_GROUPS[tabId];
	if (!tab) return [{ heading: '', items }];

	const buckets: Record<string, EntryResponse[]> = {};
	for (const rule of tab.rules) buckets[rule.heading] = [];

	for (const entry of items) {
		const n = fold(entry.titel);
		let heading = tab.fallback;
		for (const rule of tab.rules) {
			if (rule.keywords.some((kw) => n.includes(kw))) {
				heading = rule.heading;
				break;
			}
		}
		buckets[heading] ??= [];
		buckets[heading].push(entry);
	}

	const groups: EntryGroup[] = [];
	for (const heading of tab.order) {
		const list = buckets[heading];
		if (list?.length) groups.push({ heading, items: list });
	}
	const rest = buckets[tab.fallback];
	if (rest?.length) groups.push({ heading: tab.fallback, items: rest });
	return groups;
}
