// Curated calculator deep links (Tier 2). Sources:
//  - MDCalc favorites export (2026-09-02): https://www.mdcalc.com/favorites
//  - Direct /calc/<id>/<slug> URLs are stable; add rows here, no backend needed.
// Organized by discipline → optional subgroup (`group`). `keywords` are
// Diagnosen names (German + English terms).

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

export const CALCULATORS: CalculatorLink[] = [
  // Allgemein
  { name: 'BMI & BSA', url: 'https://www.mdcalc.com/calc/29/body-mass-index-bmi-body-surface-area-bsa', discipline: 'Allgemein', keywords: ['bmi', 'bsa', 'adipositas'] },
  // Kardiologie — EKG
  { name: 'QTc (Corrected QT)', url: 'https://www.mdcalc.com/calc/48/corrected-qt-interval-qtc', discipline: 'Kardiologie', group: 'EKG', keywords: ['qtc', 'ekg', 'qt', 'arrhythmie'] },
  // Kardiologie — Gefäße
  { name: 'SCORE2', url: 'https://www.mdcalc.com/calc/10499/systematic-coronary-risk-evaluation-score2', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['kvd', 'kardio', 'cardio', 'risiko', 'cvd', 'koronar'] },
  { name: 'SCORE2-OP', url: 'https://www.mdcalc.com/calc/10503/score2-older-persons-score2-op', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['kvd', 'kardio', 'risiko', 'alter', 'geriatrie'] },
  { name: 'SCORE2-Diabetes', url: 'https://www.mdcalc.com/calc/10510/score2-diabetes', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['diabetes', 'kvd', 'risiko'] },
  { name: 'ASCVD Risk (AHA/ACC 2013)', url: 'https://www.mdcalc.com/calc/3398/ascvd-atherosclerotic-cardiovascular-disease-2013-risk-calculator-aha-acc', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['ascvd', 'kardio', 'risiko', 'herzinfarkt'] },
  { name: 'PREVENT™ (CVD Events)', url: 'https://www.mdcalc.com/calc/10491/predicting-risk-cardiovascular-disease-events-prevent', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['cvd', 'kardio', 'risiko', 'prevent'] },
  { name: 'TIMI Risk Score UA/NSTEMI', url: 'https://www.mdcalc.com/calc/111/timi-risk-score-ua-nstemi', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['nstemi', 'angina', 'acs', 'akss', 'timi'] },
  { name: 'TIMI Risk Score STEMI', url: 'https://www.mdcalc.com/calc/99/timi-risk-score-stemi', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['stemi', 'herzinfarkt', 'acs', 'timi'] },
  { name: 'TIMI Risk Index', url: 'https://www.mdcalc.com/calc/665/timi-risk-index', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['acs', 'akss', 'timi'] },
  { name: 'GRACE ACS Score', url: 'https://www.mdcalc.com/calc/1099/grace-acs-risk-mortality-calculator', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['acs', 'akss', 'grace'] },
  { name: 'Marburg Heart Score', url: 'https://www.mdcalc.com/calc/4022/marburg-heart-score-mhs', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['thoraxschmerz', 'chest pain', 'khk', 'cad', 'koronar', 'angina'] },
  { name: 'MAP (Mean Arterial Pressure)', url: 'https://www.mdcalc.com/calc/74/mean-arterial-pressure-map', discipline: 'Kardiologie', group: 'Gefäße', keywords: ['blutdruck', 'map', 'hypertonie'] },
  // Kardiologie — Gerinnung
  { name: 'CHA₂DS₂-VASc Score', url: 'https://www.mdcalc.com/calc/801/cha2ds2-vasc-score-atrial-fibrillation-stroke-risk', discipline: 'Kardiologie', group: 'Gerinnung', keywords: ['vorhofflimmern', 'atrial fibrillation', 'afib', 'schlaganfall', 'stroke', 'chads'] },
  { name: 'HAS-BLED Score', url: 'https://www.mdcalc.com/calc/807/has-bled-score-major-bleeding-risk', discipline: 'Kardiologie', group: 'Gerinnung', keywords: ['blutung', 'bleeding', 'antikoagulation', 'vorhofflimmern', 'afib'] },
  { name: 'DAPT Score', url: 'https://www.mdcalc.com/calc/10016/dual-antiplatelet-therapy-dapt-score', discipline: 'Kardiologie', group: 'Gerinnung', keywords: ['dapt', 'stent', 'pci', 'antiplatelet', 'thrombozyten'] },
  { name: '4Ts Score (HIT)', url: 'https://www.mdcalc.com/calc/1787/4ts-score-heparin-induced-thrombocytopenia', discipline: 'Kardiologie', group: 'Gerinnung', keywords: ['hit', 'heparin', 'thrombozytopenie'] },
  // Pulmologie — Asthma
  { name: 'Asthma Predictive Index (API)', url: 'https://www.mdcalc.com/calc/3381/asthma-predictive-index-api', discipline: 'Pulmologie', group: 'Asthma', keywords: ['asthma', 'asthm', 'pädiatrie', 'kinder', 'kind'] },
  { name: 'Pediatric Asthma Score (PAS)', url: 'https://www.mdcalc.com/calc/3935/pediatric-asthma-score-pas', discipline: 'Pulmologie', group: 'Asthma', keywords: ['asthma', 'asthm', 'pädiatrie', 'kinder', 'kind', 'exazerbation'] },
  { name: 'PASS (Pädiatrische Asthma-Schweregrade)', url: 'https://www.mdcalc.com/calc/3383/pediatric-asthma-severity-score-pass-asthma-exacerbation-severity', discipline: 'Pulmologie', group: 'Asthma', keywords: ['asthma', 'asthm', 'pädiatrie', 'kinder', 'kind', 'exazerbation', 'pass'] },
  // Pulmologie — COPD
  { name: 'COPD Assessment Test (CAT)', url: 'https://www.mdcalc.com/calc/10161/copd-assessment-test-cat', discipline: 'Pulmologie', group: 'COPD', keywords: ['copd', 'obstruktiv'] },
  { name: 'ROX Index (HFNC)', url: 'https://www.mdcalc.com/calc/10302/rox-index-intubation-hfnc', discipline: 'Pulmologie', group: 'COPD', keywords: ['hfnc', 'rox', 'sauerstoff', 'oxygenierung', 'intubation'] },
  // Pulmologie — Pneumonie
  { name: 'CURB-65', url: 'https://www.mdcalc.com/calc/324/curb-65-score-pneumonia-severity', discipline: 'Pulmologie', group: 'Pneumonie', keywords: ['pneumonie', 'pneumonia', 'curb'] },
  // Notfall
  { name: 'Wells Score Lungenembolie', url: 'https://www.mdcalc.com/calc/115/wells-criteria-pulmonary-embolism', discipline: 'Notfall', keywords: ['lungenembolie', 'pulmonary embolism', 'wells', 'thrombose'] },
  // Neurologie
  { name: 'NIHSS', url: 'https://www.mdcalc.com/calc/715/nih-stroke-scale-score-nihss', discipline: 'Neurologie', keywords: ['stroke', 'schlaganfall', 'nihss', 'apoplex'] },
  { name: 'Glasgow Coma Scale (GCS)', url: 'https://www.mdcalc.com/calc/64/glasgow-coma-scale-score-gcs', discipline: 'Neurologie', keywords: ['gcs', 'koma', 'coma', 'bewusstsein'] },
  // Intensiv
  { name: 'SOFA Score', url: 'https://www.mdcalc.com/calc/691/sequential-organ-failure-assessment-sofa-score', discipline: 'Intensiv', keywords: ['sofa', 'icu', 'intensiv', 'sepsis'] },
  { name: 'APACHE II Score', url: 'https://www.mdcalc.com/calc/1868/apache-ii-score', discipline: 'Intensiv', keywords: ['apache', 'icu', 'intensiv'] },
  // Infektiologie
  { name: 'SIRS & Sepsis Criteria', url: 'https://www.mdcalc.com/calc/1096/sirs-sepsis-septic-shock-criteria', discipline: 'Infektiologie', keywords: ['sepsis', 'sirs'] },
  { name: 'qSOFA', url: 'https://www.mdcalc.com/calc/2654/qsofa-quick-sofa-score-sepsis', discipline: 'Infektiologie', keywords: ['sepsis', 'qsofa'] },
  { name: 'PEN-FAST (Penicillin-Allergie)', url: 'https://www.mdcalc.com/calc/10422/penicillin-allergy-decision-rule-pen-fast', discipline: 'Infektiologie', keywords: ['penicillin', 'allergie', 'allergy'] },
  // Gastro & Hepatologie
  { name: 'BISAP Score (Pankreatitis)', url: 'https://www.mdcalc.com/calc/1735/bisap-score-pancreatitis-mortality', discipline: 'Gastro & Hepatologie', keywords: ['pankreatitis', 'pancreatitis', 'bisap'] },
  { name: 'FIB-4 Index (Leberfibrose)', url: 'https://www.mdcalc.com/calc/2200/fibrosis-4-fib-4-index-liver-fibrosis', discipline: 'Gastro & Hepatologie', keywords: ['leber', 'liver', 'fibrose', 'fib-4', 'zirrhose'] },
  // Nephrologie
  { name: 'CKD-EPI GFR', url: 'https://www.mdcalc.com/calc/3939/ckd-epi-equations-glomerular-filtration-rate-gfr', discipline: 'Nephrologie', keywords: ['gfr', 'niere', 'ckd', 'renal', 'kreatinin'] },
  { name: 'MDRD GFR', url: 'https://www.mdcalc.com/calc/76/mdrd-gfr-equation', discipline: 'Nephrologie', keywords: ['gfr', 'niere', 'ckd', 'renal'] },
  { name: 'Creatinine Clearance (Cockcroft-Gault)', url: 'https://www.mdcalc.com/calc/43/creatinine-clearance-cockcroft-gault-equation', discipline: 'Nephrologie', keywords: ['kreatinin', 'creatinine', 'gfr', 'niere'] },
  { name: 'nieren.app Rechner (ÖGN)', url: 'https://nieren.app/calculator', discipline: 'Nephrologie', keywords: ['niere', 'nephrologie', 'ckd', 'gfr', 'elektrolyt', 'dialyse', 'albuminurie'] },
  { name: 'nieren.app Guidelines (ÖGN)', url: 'https://nieren.app/guidelines', discipline: 'Nephrologie', keywords: ['niere', 'nephrologie', 'leitlinie', 'kdigo'] },
  // Labor
  { name: 'Calcium Correction (Albumin)', url: 'https://www.mdcalc.com/calc/31/calcium-correction-hypoalbuminemia', discipline: 'Labor', keywords: ['kalzium', 'calcium', 'albumin'] },
];

export function calculatorMatches(calc: CalculatorLink, term: string): boolean {
  const t = term.toLowerCase();
  return calc.name.toLowerCase().includes(t) || calc.keywords.some((k) => t.includes(k) || k.includes(t));
}

/** Discipline color lookup for chip accents. */
export const DISCIPLINE_COLORS: Record<string, string> = Object.fromEntries(
  DISCIPLINES.map((d) => [d.name, d.color])
);
