-- ============================================================
-- Migration 005: Unified Tagging System
-- ============================================================
-- 1. Dokumenttyp becomes a real lookup table (dokumenttypen)
-- 2. Ordner-Labels become a real lookup table (ordner_labels) + M2M junction
-- 3. Backward compat: old `dokumenttyp` column and `source_hierarchy`
--    JSONB column are kept during rollout.
-- Follows the existing Fachgebiet / Diagnose / Symptom pattern.
-- ============================================================

-- ------------------------------------------------------------
-- 1. DOKUMENTTYPEN (Document Types) lookup table
-- ------------------------------------------------------------
CREATE TABLE dokumenttypen (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(50) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 2. Seed dokumenttypen with current hardcoded values
-- ------------------------------------------------------------
INSERT INTO dokumenttypen (name) VALUES
    ('Leitlinie'),
    ('SOP'),
    ('Studie'),
    ('Fachgebiet'),
    ('Pharma'),
    ('Fragebogen'),
    ('Infoblatt'),
    ('Red Flags'),
    ('Prüfung'),
    ('Fortbildung'),
    ('Nachschlagen'),
    ('Fall');

-- ------------------------------------------------------------
-- 3. Add FK column on knowledge_entries (nullable during rollout)
-- ------------------------------------------------------------
ALTER TABLE knowledge_entries
    ADD COLUMN dokumenttyp_id INTEGER REFERENCES dokumenttypen(id) ON DELETE SET NULL;

CREATE INDEX idx_knowledge_entries_dokumenttyp_id ON knowledge_entries(dokumenttyp_id);

-- ------------------------------------------------------------
-- 4. Migrate existing dokumenttyp string values to IDs
-- ------------------------------------------------------------
UPDATE knowledge_entries ke
SET dokumenttyp_id = d.id
FROM dokumenttypen d
WHERE ke.dokumenttyp = d.name;

-- ------------------------------------------------------------
-- 5. ORDNER_LABELS (Folder Labels) lookup table
-- ------------------------------------------------------------
CREATE TABLE ordner_labels (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL UNIQUE,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(50) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 6. M2M junction: knowledge_entries <-> ordner_labels
-- ------------------------------------------------------------
CREATE TABLE entry_ordner_label (
    entry_id    INTEGER REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    label_id    INTEGER REFERENCES ordner_labels(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, label_id)
);

CREATE INDEX idx_entry_ordner_label_label ON entry_ordner_label(label_id);

-- ------------------------------------------------------------
-- 7. Migrate existing source_hierarchy data into ordner_labels
-- ------------------------------------------------------------
INSERT INTO ordner_labels (name, source)
SELECT DISTINCT jsonb_array_elements_text(source_hierarchy), 'folder'
FROM knowledge_entries
WHERE source_hierarchy IS NOT NULL
  AND jsonb_array_length(source_hierarchy) > 0
ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------------------
-- 8. Link entries to their migrated folder labels (M2M junction)
-- ------------------------------------------------------------
INSERT INTO entry_ordner_label (entry_id, label_id)
SELECT ke.id, ol.id
FROM knowledge_entries ke,
     jsonb_array_elements_text(ke.source_hierarchy) AS label
     JOIN ordner_labels ol ON ol.name = label
WHERE ke.source_hierarchy IS NOT NULL
ON CONFLICT DO NOTHING;
