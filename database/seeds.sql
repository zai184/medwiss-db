-- ============================================================
-- Test Data Seeds for Medizinische Wissensdatenbank
-- ============================================================
-- All data is anonymized/fictional for testing purposes only
-- No real patient data

-- ============================================================
-- FACHGEBIETE (Specialties)
-- ============================================================

INSERT INTO fachgebiete (name, beschreibung) VALUES
('Allgemeinmedizin', 'Hausärztliche Versorgung, Primärversorgung'),
('Kardiologie', 'Herz- und Gefäßerkrankungen'),
('Pulmologie', 'Atemwegs- und Lungenerkrankungen'),
('Innere Medizin', 'Internistische Erkrankungen'),
('Psychiatrie', 'Psychische Erkrankungen'),
('Neurologie', 'Erkrankungen des Nervensystems'),
('Orthopädie', 'Bewegungsapparat'),
('Dermatologie', 'Hauterkrankungen');

-- ============================================================
-- DIAGNOSEN (Diagnoses - fictional ICD codes)
-- ============================================================

INSERT INTO diagnosen (code, name, beschreibung) VALUES
('I25.9', 'Koronare Herzkrankheit (KHK)', 'Chronische Durchblutungsstörung des Herzens'),
('J44.9', 'COPD', 'Chronisch obstruktive Lungenerkrankung'),
('F32.1', 'Depression', 'Mittelgradige depressive Episode'),
('I10.0', 'Hypertonie', 'Bluthochdruck'),
('E11.9', 'Diabetes mellitus Typ 2', 'Altersdiabetes ohne Komplikationen'),
('J18.9', 'Pneumonie', 'Lungenentzündung'),
('K29.5', 'Gastritis', 'Magenschleimhautentzündung'),
('M54.5', 'Rückenschmerz', 'Unspezifischer Kreuzschmerz'),
('F41.1', 'Angststörung', 'Generalisierte Angststörung'),
('I21.0', 'Herzinfarkt', 'Akuter Vorderwandinfarkt');

-- ============================================================
-- SYMPTOME (Symptoms)
-- ============================================================

INSERT INTO symptome (name, beschreibung) VALUES
('Atemnot', 'Dyspnoe, Luftnot'),
('Brustschmerz', 'Thoraxschmerz,pektanginöse Beschwerden'),
('Kopfschmerz', 'Cephalgie, Spannungskopfschmerz'),
('Müdigkeit', 'Fatigue, Abgeschlagenheit'),
('Schwindel', 'Vertigo, Drehschwindel'),
('Übelkeit', 'Nausea, Brechreiz'),
('Fieber', 'Erhöhte Körpertemperatur >38°C'),
('Husten', 'Tussis, trocken oder produktiv'),
('Bauchschmerz', 'Abdominalschmerz'),
('Ödeme', 'Wassereinlagerungen, Schwellungen'),
('Palpitationen', 'Herzrasen, Herzstolpern'),
('Nikotinabusus', 'Tabakkonsum'),
('Gewichtsverlust', 'Ungewollte Abnahme des Körpergewichts'),
('Nykturie', 'Nächtliches Wasserlassen'),
('Dysphagie', 'Schluckstörung');

-- ============================================================
-- KNOWLEDGE ENTRIES (20+ entries across categories)
-- ============================================================

-- SOPs
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('SOP: Akuter Brustschmerz', 'Standardprozedur zur Abklärung akuter Brustschmerzen', 
'# SOP: Akuter Brustschmerz

## Indikation
Jeder Patient mit akutem Brustschmerz >5 min

## Diagnostik
1. Vitalzeichen prüfen
2. 12-Kanal-EKG innerhalb 10 min
3. Troponin-Bestimmung
4. Anamnese (QUALITY-Schema)

## Alarmzeichen
- EKG: ST-Hebungen
- Hypotonie <90 mmHg
- Kalter Schweiß

## Weiteres Vorgehen
- Bei STEMI: Direkte Herzkatheterisierung
- Bei NSTEMI: Troponin-Verlauf, Risikostratifizierung
- Bei unklar: Beobachtung, weitere Diagnostik',
'SOP-Katalog 2024', 'Leitlinie', 'fortgeschritten', 2),

('SOP: Atemnot in der Praxis', 'Abklärung akuter Dyspnoe',
'# SOP: Atemnot

## Ursachen
- Kardial: Herzinsuffizienz, Lungenödem
- Pulmonal: COPD, Pneumonie, PE
- Sonst: Anämie, Hyperventilation

## Diagnostik
1. SpO2, Atemfrequenz
2. Auskultation
3. EKG bei V.a. kardiale Ursache
4. BGA bei respiratorischer Symptomatik

## Red Flags
- SpO2 <90%
- Atemfrequenz >25/min
- Zyanose
- Stridor',
'Leitlinien DEGAM', 'Leitlinie', 'experte', 2),

('SOP: Blutzuckereinstellung Typ 2', 'Therapieeskalation bei Diabetes',
'# SOP: Blutzuckereinstellung

## Basistherapie
- Lebensstiländerung
- Metformin als First-Line

## Eskalation bei HbA1c >7%
1. +SGLT2-Inhibitor oder GLP-1-Agonist
2. +Basalinsulin
3. Intensivierte Insulintherapie

## Zielwerte
- Junge Patienten: HbA1c <7%
- Ältere/morbide: HbA1c <8%',
'NVL Diabetes', 'Studie', 'fortgeschritten');

-- Leitlinien
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('Leitlinie KHK', 'Diagnostik und Therapie der KHK',
'# Leitlinie KHK 2023

## Diagnosekriterien
- Typische Angina: Stenokardie + Belastung
- EKG: ST-Senkungen
- Belastungstest positiv
- Koronarangiographie: Stenosierung >70%

## Therapie
### Medikamentös
- ASS 100mg
- Statin (Ziel LDL <70mg/dl)
- Betablocker
- ACE-Hemmer/ARB

### Intervention
- PCI bei symptomatischer KHK
- Bypass-OP bei 3-VK oder Hauptstamm',
'ESC Guidelines 2023', 'Leitlinie', 'experte', 2),

('NVL COPD Leitlinie', 'Nationale VersorgungsLeitlinie COPD',
'# NVL COPD

## Diagnose
- FEV1/FVC <70% nach Bronchodilatation
- symptoms >3 Monate/Jahr

## Therapiestufen
1. LAMA bei wenig Symptomen
2. LABA+LAMA bei persistierenden Symptomen
3. +ICS bei Exazerbationen

## Exazerbation
- Amoxicillin/Clavulansäure 5d
- Prednisolon 30-40mg 5d
- Bei Ateminsuffizienz: O2, NIV',
'NVL COPD 2024', 'Leitlinie', 'fortgeschritten', 2),

('Leitlinie Hypertonie', 'Bluthochdruck-Diagnostik und -Therapie',
'# Leitlinie Hypertonie

## Definition
- Praxismessung: ≥140/90 mmHg
- 24h-MBSS: ≥130/80 mmHg

## Diagnostik
- 24h-Blutdruckmessung
- Labor: Kreatinin, EFK, Glukose, Lipide
- Urin: Protein, Mikroalbumin
- EKG

## Therapieziele
- <140/90 mmHg (Praxis)
- <135/85 mmHg (zuhause)
- Ältere: <150/90 mmHg',
'ESH/ESC 2023', 'Leitlinie', 'fortgeschritten');

-- Studien
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('SGLT2-Hemmer bei Herzinsuffizienz', 'Metaanalyse zu SGLT2-Inhibitoren',
'# SGLT2-Hemmer bei HFrEF

## Studienlage
- DAPA-HF: Dapagliflozin reduziert Hospitalisierung um 30%
- EMPEROR-Reduced: Empagliflozin +25% Reduktion CV-Mortalität

## Mechanismus
- Osmotische Diurese
- Reduktion kardialer Vorlast
- Stoffwechseleffekte (Ketone)

## Praxisrelevanz
- SGLT2i bei HFrEF unabhängig von Diabetesindikation
- Kombination mit ARNI empfohlen',
'NEJM 2023', 'Studie', 'experte', 2),

('COVID-19 Langzeitfolgen', 'Systematic Review Langzeit-COVID',
'# Long-COVID

## Definition
- Symptome >12 Wochen nach Infektion
- Multisystemerkrankung

## Häufigste Symptome
- Fatigue (50%)
- Dyspnoe (30%)
- Kognitive Dysfunktion (30%)
- Taste/Smell (20%)

## Pathophysiologie
- Viruspersistenz?
- Autoimmunprozesse
- Endothelschädigung

## Therapie
- Symptomatisch
- multidisziplinär',
'Lancet 2024', 'Studie', 'experte');

-- Red Flags
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('Red Flags bei Rückenschmerz', 'Warnsignale für ernste Ursachen',
'# Red Flags Rückenschmerz

## Alarmzeichen
- Fieber + Rückenschmerz → Infektion?
- Gewichtsverlust + Nachtschweiß → Tumor?
- Stuhl-/Inkontinenz → Cauda-Syndrom
- Bilaterale Beinschwäche → Notfall!
- Anamnese: Malignom → Pathologische Fraktur

## Rote Flagge Checklist
1. Trauma?
2. Fieber?
3. IV-Drogen?
4. Immunsuppression?
5. Malignom in Anamnese?
6. Alter >50 bei Erstmanifestation?
7. Neurologische Defizite?

## Bei Cauda-Syndrom
→ Sofort MRT, neurochirurgische Vorstellung',
'Leitlinien Orthopädie', 'Leitlinie', 'experte', 2),

('Red Flags Kopfschmerz', 'Wann ist Kopfschmerz ein Notfall?',
'# Red Flags Kopfschmerz

## Notfallindikationen
- Erstmaliger "Vernichtungskopfschmerz"
- Fieber + Nackensteife → Meningitis
- Papillenödem → Hirndruck
- Fokale Defizite → Schlaganfall
- Bewusstseinsstörung
- Trauma

## Diagnostik
- CCT bei allen Red Flags
- Lumbalpunktion bei V.a. Meningitis
- MRT bei V.a. intrazerebrale Pathologie',
'Deutsche Migränehilfe', 'Leitlinie', 'experte');

-- Fragebögen
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('PHQ-9 Depressionsfragebogen', 'Standardisierter Fragebogen zur Depressionsscreening',
'# PHQ-9

## Fragen (Häufigkeit in letzten 2 Wochen)
1. Wenig Interesse/Freude
2. Niedergeschlagenheit/Depression
3. Einschlafstörungen/Schlafstörungen
4. Müdigkeit/Energieverlust
5. Appetitveränderungen
6. Selbstwertgefühl/Schuldgefühle
7. Konzentrationsschwierigkeiten
8. Psychomotorische Agitation/Retardierung
9. Suizidgedanken

## Auswertung
- 0-4: Keine Depression
- 5-9: Leichte Depression
- 10-14: Mittelgradige Depression
- 15-19: Mittelgradig bis schwere Depression
- 20-27: Schwere Depression

## Cut-off: ≥10 → Weiterführende Diagnostik',
'PHQ-9 Originalfragebogen', 'Leitlinie', 'fortgeschritten', 3),

('GAD-7 Angstfragebogen', 'Fragebogen zur generalisierten Angststörung',
'# GAD-7

## Fragen
1. Nervosität/Ängstlichkeit
2. Nicht kontrollierbares Sorgen
3. Sorgen über verschiedene Dinge
4. Schwierigkeiten zu entspannen
5. Ruhelosigkeit
6. Leichte Erschöpfbarkeit
7. Reizbarkeit

## Auswertung
- 0-4: Minimal
- 5-9: Leicht
- 10-14: Mittel
- 15-21: Schwer',
'GAD-7 Manual', 'Leitlinie', 'fortgeschritten');

-- Infoblätter
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('Infoblatt Bluthochdruck', 'Patienteninformation Blutdruck',
'# Bluthochdruck - Was Sie wissen sollten

## Was ist Bluthochdruck?
Ein dauerhaft erhöhter Blutdruck über 140/90 mmHg

## Risiken
- Schlaganfall
- Herzinfarkt
- Nierenschäden
- Augenschäden

## Was Sie tun können
- Salz reduktion (<5g/Tag)
- Regelmäßige Bewegung (30min/d)
- Gewicht reduzieren bei Übergewicht
- Alkohol meiden
- Nicht rauchen

## Medikamente
- Regelmäßig einnehmen
- Nie eigenmächtig absetzen
- Bei Nebenwirkungen Arzt informieren',
'Patienteninformation KBV', 'Leitlinie', 'anfaenger', 3),

('Infoblatt Diabetes Typ 2', 'Leben mit Diabetes',
'# Diabetes Typ 2 - Was nun?

## Was ist Diabetes?
Der Körper kann Zucker aus dem Blut nicht mehr ausreichend aufnehmen

## Symptome
- Häufiges Wasserlassen
- Durst
- Müdigkeit
- Schlecht heilende Wunden

## Ziele
- HbA1c <7%
- Blutdruck <140/85
- LDL <100 mg/dl

## Selbstkontrolle
- Blutzucker messen
- Fußkontrolle täglich
- Regelmäßige Arztbesuche',
'Deutsche Diabeteshilfe', 'Leitlinie', 'anfaenger');

-- Fälle (anonymisierte Lehrfälle - keine echten Patienten)
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('Fall: 65j Patient mit Brustschmerz', 'KHK-Diagnostik bei typischer Angina',
'# Lehrfall: Brustschmerz

## Anamnese
65-jähriger Patient, männlich
- Seit 3 Monaten belastungsabhängige Brustenge
- Treppen steigen: nach 2 Stockwerken
- In Ruhe: keine Beschwerden

## Risikofaktoren
- Hypertonie seit 10 Jahren
- Raucher (30 Packungsjahre)
- Vater: Herzinfarkt mit 60

## Befund
- RR 150/95 mmHg
- Puls 78/min
- Kein Herzgeräusch
- EKG: Linkstyp, keine ST-Veränderungen

## Diagnose
Verdacht auf stabile Angina pectoris bei V.a. KHK

## Lernziele
1. Typische vs. atypische Angina
2. Risikofaktoren评估
3. Diagnostikpfad',
'Fallkonferenz Innere', 'Fall', 'fortgeschritten', 2),

('Fall: 45j Patient mit Atemnot', 'COPD-Exazerbation',
'# Lehrfall: Atemnot

## Anamnese
45-jährige Patientin
- Seit 5 Jahren bekannte COPD (Gold 2)
- 2 Packungen Zigaretten/Tag seit 20 Jahren
- Akute Verschlechterung seit 3 Tagen
- Mehr Husten, gelblich-schukettes Sputum

## Befund
- SpO2 88% (Raumluft)
- Atemfrequenz 24/min
- Trommelstockfinger?
- Thorax: Überblähung, verlängertes Exspirium

## Diagnose
COPD-Exazerbation mit respiratorischer Partialinsuffizienz

## Lernziele
1. Exazerbationskriterien
2. When is NIV necessary?
3. Antibiotic therapy criteria',
'Fallkonferenz Pneumologie', 'Fall', 'fortgeschritten', 3),

('Fall: 30j Patient mit Kopfschmerz', 'Migräne vs. Spannungskopfschmerz',
'# Lehrfall: Kopfschmerz

## Anamnese
30-jährige Patientin
- Seit Jugend Migräne (4-5/Monat)
- Jetzt neue Kopfschmerzen seit 3 Monaten
- Täglich, dumpf-diffus
- Keine Übelkeit, keine Photophobie

## Familienanamnese
- Mutter: Migräne
- Vater: Hypertonie

## Befund
- Neurologischer Status: unauffällig
- Kein Papillenödem
- Keine Nackensteife

## Diagnose
Migräne + neuer Spannungskopfschmerz (Medication Overuse?)

## Lernziele
1. Migräne-Diagnosekriterien
2. Red Flags ausschließen
3. Medication Overuse Headache',
'Fallkonferenz Neurologie', 'Fall', 'fortgeschritten');

-- Fortbildung
INSERT INTO knowledge_entries (titel, zusammenfassung, inhalt, quelle, dokumenttyp, schwierigkeit) VALUES
('Fortbildung: EKG-Basics', 'EKGInterpretation für Anfänger',
'# EKG-Fortbildung Grundlagen

## Grundlagen
- 10 Elektroden, 12 Ableitungen
- Papiergeschwindigkeit: 25mm/s
- Standardisierung: 1mV = 10mm

## Bestimmung Herzfrequenz
- Regel: 1500 / Anzahl Kästchen zwischen zwei R-Zacken
- Tachykardie: >100/min
- Bradykardie: <60/min

## Bestimmung Herzrhythmus
- Regelmäßig?
- P-Welle vor QRS?
- PQ-Dauer normal (120-200ms)?

## Achsenbestimmung
- Linkstyp: I pos, III neg
- Rechtstyp: I neg, III pos
- Steillagetyp: I pos, III pos

## Ischämiezeichen
- ST-Hebung: Transmurale Ischämie
- ST-Senkung: Subendokardiale Ischämie
- T-Negativierung: Ischämie oder Narbe',
'CME-Fortbildung Kardiologie', 'Studie', 'fortgeschritten', 2),

('Fortbildung: Impfungen Erwachsene', 'Impfkalender und Indikationen',
'# Impffortbildung

## Standardimpfungen Erwachsene
- Tdap alle 10 Jahre
- Masern einmalig wenn nach 1970 geboren
- Influenza jährlich (>60 Jahre)
- Pneumokokken >65 Jahre
- Zoster (Totimpfstoff) >50 Jahre

## Indikationsimpfungen
- FSME: Risikogebiete
- Hepatitis A/B: Risikogruppen
- Meningokokken: Asplenie

## Impfstatus prüfen
- Bei jedem Praxisbesuch
- Dokumentation in Impfpass
- Nachholimpfungen sofort',
'Robert Koch Institut', 'Leitlinie', 'fortgeschritten', 3),

('Fortbildung: Antimikrobielle Therapie', 'Antibiotika-Leitfaden',
'# Antibiotikatherapie

## Häufigste Infektionen

### Atemwege
- Ambulant: Amoxicillin 3x1g 5-7d
- Bei Penicillinallergie: Makrolid

### Harnwege
- Unkompliziert: Fosfomycin 3g Einmaldosis
- Kompliziert: Ciprofloxacin 2x500mg 7d

### Haut
- Erysipel: Penicillin G 3x5MIO 10d
- Abszess: Clindamycin + chirurgische Sanierung

## Wichtige Regeln
- Kulturen vor Therapie
- Antibiotika-Only bei bakteriell
- Therapiedauer nicht verlängern
- SPECT in der Praxis',
'Paul-Ehrlich-Gesellschaft', 'Studie', 'experte');

-- ============================================================
-- VERKNÜPFUNGEN (M2M Relations)
-- ============================================================

-- Entry 1: SOP Akuter Brustschmerz
INSERT INTO entry_fach (entry_id, fach_id) VALUES (1, 2); -- Kardiologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (1, 1), (1, 10); -- KHK, Herzinfarkt
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (1, 2); -- Brustschmerz

-- Entry 2: SOP Atemnot
INSERT INTO entry_fach (entry_id, fach_id) VALUES (2, 3); -- Pulmologie
INSERT INTO entry_fach (entry_id, fach_id) VALUES (2, 2); -- Kardiologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (2, 2); -- COPD
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (2, 1); -- Atemnot

-- Entry 3: SOP Blutzucker
INSERT INTO entry_fach (entry_id, fach_id) VALUES (3, 4); -- Innere Medizin
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (3, 5); -- Diabetes
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (3, 4); -- Müdigkeit

-- Entry 4: Leitlinie KHK
INSERT INTO entry_fach (entry_id, fach_id) VALUES (4, 2); -- Kardiologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (4, 1); -- KHK
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (4, 2), (4, 11); -- Brustschmerz, Palpitationen

-- Entry 5: NVL COPD
INSERT INTO entry_fach (entry_id, fach_id) VALUES (5, 3); -- Pulmologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (5, 2); -- COPD
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (5, 1), (5, 8); -- Atemnot, Husten

-- Entry 6: Leitlinie Hypertonie
INSERT INTO entry_fach (entry_id, fach_id) VALUES (6, 4); -- Innere Medizin
INSERT INTO entry_fach (entry_id, fach_id) VALUES (6, 2); -- Kardiologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (6, 4); -- Hypertonie

-- Entry 7: SGLT2-Hemmer Studie
INSERT INTO entry_fach (entry_id, fach_id) VALUES (7, 2); -- Kardiologie
INSERT INTO entry_fach (entry_id, fach_id) VALUES (7, 4); -- Innere Medizin
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (7, 5); -- Diabetes

-- Entry 8: COVID Langzeitfolgen
INSERT INTO entry_fach (entry_id, fach_id) VALUES (8, 4); -- Innere Medizin
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (8, 1), (8, 4), (8, 3); -- Atemnot, Müdigkeit, Kopfschmerz

-- Entry 9: Red Flags Rückenschmerz
INSERT INTO entry_fach (entry_id, fach_id) VALUES (9, 7); -- Orthopädie
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (9, 9); -- Bauchschmerz

-- Entry 10: Red Flags Kopfschmerz
INSERT INTO entry_fach (entry_id, fach_id) VALUES (10, 6); -- Neurologie
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (10, 3); -- Kopfschmerz

-- Entry 11: PHQ-9
INSERT INTO entry_fach (entry_id, fach_id) VALUES (11, 5); -- Psychiatrie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (11, 3); -- Depression
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (11, 4), (11, 3); -- Müdigkeit, Kopfschmerz

-- Entry 12: GAD-7
INSERT INTO entry_fach (entry_id, fach_id) VALUES (12, 5); -- Psychiatrie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (12, 9); -- Angststörung
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (12, 4); -- Müdigkeit

-- Entry 13: Infoblatt Bluthochdruck
INSERT INTO entry_fach (entry_id, fach_id) VALUES (13, 1); -- Allgemeinmedizin
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (13, 4); -- Hypertonie

-- Entry 14: Infoblatt Diabetes
INSERT INTO entry_fach (entry_id, fach_id) VALUES (14, 4); -- Innere Medizin
INSERT INTO entry_fach (entry_id, fach_id) VALUES (14, 1); -- Allgemeinmedizin
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (14, 5); -- Diabetes

-- Entry 15: Fall Brustschmerz
INSERT INTO entry_fach (entry_id, fach_id) VALUES (15, 2); -- Kardiologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (15, 1); -- KHK
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (15, 2); -- Brustschmerz

-- Entry 16: Fall Atemnot
INSERT INTO entry_fach (entry_id, fach_id) VALUES (16, 3); -- Pulmologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (16, 2); -- COPD
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (16, 1), (16, 8); -- Atemnot, Husten

-- Entry 17: Fall Kopfschmerz
INSERT INTO entry_fach (entry_id, fach_id) VALUES (17, 6); -- Neurologie
INSERT INTO entry_diagnose (entry_id, diagnose_id) VALUES (17, 3); -- Depression
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (17, 3); -- Kopfschmerz

-- Entry 18: EKG-Fortbildung
INSERT INTO entry_fach (entry_id, fach_id) VALUES (18, 2); -- Kardiologie

-- Entry 19: Impfungen
INSERT INTO entry_fach (entry_id, fach_id) VALUES (19, 1); -- Allgemeinmedizin
INSERT INTO entry_fach (entry_id, fach_id) VALUES (19, 4); -- Innere Medizin

-- Entry 20: Antibiotikatherapie
INSERT INTO entry_fach (entry_id, fach_id) VALUES (20, 1); -- Allgemeinmedizin
INSERT INTO entry_fach (entry_id, fach_id) VALUES (20, 4); -- Innere Medizin
INSERT INTO entry_symptom (entry_id, symptom_id) VALUES (20, 6); -- Übelkeit
