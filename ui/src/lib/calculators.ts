// Curated calculator deep links are live-parsed from `md/calculators.txt` in the
// corpus (GET /api/v1/calculators, same pattern as medlinks.txt). This module
// keeps only presentation: box definitions, colors, matching.
// Add favorites = add a line to calculators.txt — no rebuild.

export interface DisciplineDef {
  name: string;
  color: string;
  /** Subgroup order; calculators without `group` render first in their box. */
  groups?: string[];
}

export interface CalculatorLink {
  name: string;
  url: string;
  discipline: string;
  group?: string;
  keywords: string[];
}

export const DISCIPLINES: DisciplineDef[] = [
  { name: 'Allgemein', color: '#64748b' },
  { name: 'Kardiologie', color: '#ef4444', groups: ['EKG', 'Gefäße', 'Gerinnung'] },
  { name: 'Pulmologie', color: '#0ea5e9', groups: ['Asthma', 'COPD', 'Pneumonie'] },
  { name: 'Notfall', color: '#dc2626' },
  { name: 'Intensiv', color: '#f97316' },
  { name: 'Infektiologie', color: '#eab308' },
  { name: 'Gastro & Hepatologie', color: '#10b981' },
  { name: 'Nephrologie', color: '#14b8a6' },
  { name: 'Labor', color: '#a855f7' },
];

const DEFAULT_COLOR = '#64748b';

/** Discipline boxes: defined DISCIPLINES plus any disciplines found in calculators.txt. */
export function disciplineBoxes(calcs: CalculatorLink[]): DisciplineDef[] {
  const known = new Set(DISCIPLINES.map((d) => d.name));
  const extra = [...new Set(calcs.map((c) => c.discipline).filter((n) => !known.has(n)))];
  return [...DISCIPLINES, ...extra.map((name) => ({ name, color: DEFAULT_COLOR }))];
}

export function calculatorMatches(calc: CalculatorLink, term: string): boolean {
  const t = term.toLowerCase();
  return calc.name.toLowerCase().includes(t) || calc.keywords.some((k) => t.includes(k) || k.includes(t));
}

/** Discipline color lookup for chip accents. */
export const DISCIPLINE_COLORS: Record<string, string> = Object.fromEntries(
  DISCIPLINES.map((d) => [d.name, d.color])
);
