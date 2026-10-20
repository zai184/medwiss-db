-- ============================================================
-- Medical Knowledge Database Schema
-- PostgreSQL 15+
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- LOOKUP TABLES (Reference Data)
-- ============================================================

-- Specialties/Fields of Medicine
CREATE TABLE fachgebiete (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    beschreibung TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(20) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fachgebiete_name ON fachgebiete(name);

-- Diagnoses (ICD-10 based for structure, not real data)
CREATE TABLE diagnosen (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20) NOT NULL UNIQUE,  -- e.g., "J18.9" for pneumonia
    name        VARCHAR(255) NOT NULL,
    beschreibung TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(20) NOT NULL DEFAULT 'seed',
    icd11_code  VARCHAR(20),               -- WHO ICD-11 code (enrichment via admin classify)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_diagnosen_code ON diagnosen(code);
CREATE INDEX idx_diagnosen_name ON diagnosen(name);

-- Symptoms
CREATE TABLE symptome (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL UNIQUE,
    beschreibung TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(20) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Document Types
CREATE TABLE dokumenttypen (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(20) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dokumenttypen_name ON dokumenttypen(name);

-- Ordner Labels (folder-derived / user-editable labels)
CREATE TABLE ordner_labels (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL UNIQUE,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    source      VARCHAR(20) NOT NULL DEFAULT 'seed',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ordner_labels_name ON ordner_labels(name);

-- ============================================================
-- USER AUTHENTIFICATION
-- ============================================================

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'editor', 'viewer')),
    vorname         VARCHAR(100),
    nachname        VARCHAR(100),
    aktiv           BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- MAIN TABLE: Knowledge Entries
-- ============================================================

CREATE TABLE knowledge_entries (
    id              SERIAL PRIMARY KEY,
    titel           VARCHAR(500) NOT NULL,
    zusammenfassung  TEXT,                     -- Abstract/summary
    inhalt          TEXT NOT NULL,            -- Full content (markdown)
    quelle          VARCHAR(500),             -- Source/reference
    schwierigkeit   VARCHAR(20),              -- 'anfaenger', 'fortgeschritten', 'experte'
    unterkategorie  VARCHAR(100),             -- Deepest folder-derived subcategory label
    dokumenttyp     VARCHAR(50),              -- Document type (Leitlinie, SOP, Studie, …)
    dokumenttyp_id  INTEGER REFERENCES dokumenttypen(id) ON DELETE SET NULL,  -- FK to lookup table
    source_hierarchy JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Folder-derived labels
    -- Source file tracking (filesystem is the source of truth)
    source_path     TEXT,                      -- Original file path for imported entries
    file_hash       VARCHAR(64),               -- SHA-256 hash of source file

    -- FTS (Full-Text Search) - automatically updated via trigger
    search_vector   TSVECTOR,

    -- Vector embedding for similarity search (1536 dimensions for text-embedding models)
    embedding       vector(1536),

    -- Metadata
    version         INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    created_by      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by      INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- GIN Index for Full-Text Search
CREATE INDEX idx_knowledge_entries_fts ON knowledge_entries USING GIN(search_vector);

-- GIN Index for pg_trgm fuzzy matching on title
CREATE INDEX idx_knowledge_entries_title_trgm ON knowledge_entries USING GIN(titel gin_trgm_ops);

CREATE INDEX idx_knowledge_entries_dokumenttyp ON knowledge_entries(dokumenttyp);
CREATE INDEX idx_knowledge_entries_dokumenttyp_id ON knowledge_entries(dokumenttyp_id);
CREATE INDEX idx_knowledge_entries_schwierigkeit ON knowledge_entries(schwierigkeit);
CREATE INDEX idx_knowledge_entries_unterkategorie ON knowledge_entries(unterkategorie);
CREATE INDEX idx_knowledge_entries_created_at ON knowledge_entries(created_at DESC);

-- ivfflat index for ANN (Approximate Nearest Neighbor) similarity search on embeddings
CREATE INDEX idx_knowledge_entries_embedding ON knowledge_entries USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);


-- ============================================================
-- MANY-TO-MANY JUNCTION TABLES
-- ============================================================

-- Entry <-> Specialty
CREATE TABLE entry_fach (
    entry_id    INTEGER REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    fach_id     INTEGER REFERENCES fachgebiete(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, fach_id)
);

CREATE INDEX idx_entry_fach_fach ON entry_fach(fach_id);

-- Entry <-> Diagnosis
CREATE TABLE entry_diagnose (
    entry_id    INTEGER REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    diagnose_id INTEGER REFERENCES diagnosen(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, diagnose_id)
);

CREATE INDEX idx_entry_diagnose_diagnose ON entry_diagnose(diagnose_id);

-- Entry <-> Symptom
CREATE TABLE entry_symptom (
    entry_id    INTEGER REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    symptom_id  INTEGER REFERENCES symptome(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, symptom_id)
);

-- Entry <-> Ordner Label
CREATE TABLE entry_ordner_label (
    entry_id    INTEGER REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    label_id    INTEGER REFERENCES ordner_labels(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, label_id)
);

CREATE INDEX idx_entry_ordner_label_label ON entry_ordner_label(label_id);

-- ============================================================
-- AUDIT LOG (Compliance)
-- ============================================================

CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    tisch_name      VARCHAR(50) NOT NULL,
    aktion          VARCHAR(20) NOT NULL CHECK (aktion IN ('INSERT', 'UPDATE', 'DELETE')),
    datensatz_id    INTEGER,                    -- The affected row's PK
    alte_daten      JSONB,                      -- Previous state (for UPDATE/DELETE)
    neue_daten      JSONB,                      -- New state (for INSERT/UPDATE)
    benutzer_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ip_adresse      VARCHAR(45),
    zeitstempel     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for audit log queries
CREATE INDEX idx_audit_log_tisch ON audit_log(tisch_name);
CREATE INDEX idx_audit_log_aktion ON audit_log(aktion);
CREATE INDEX idx_audit_log_zeitstempel ON audit_log(zeitstempel DESC);
CREATE INDEX idx_audit_log_benutzer ON audit_log(benutzer_id);
CREATE INDEX idx_audit_log_datensatz ON audit_log(tisch_name, datensatz_id);

-- ============================================================
-- TRIGGER: Auto-update search_vector
-- ============================================================

CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('german', COALESCE(NEW.titel, '')), 'A') ||
        setweight(to_tsvector('german', COALESCE(NEW.zusammenfassung, '')), 'B') ||
        setweight(to_tsvector('german', COALESCE(NEW.inhalt, '')), 'C');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_knowledge_entries_search_vector
    BEFORE INSERT OR UPDATE ON knowledge_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- ============================================================
-- TRIGGER: Audit Log for knowledge_entries
-- ============================================================

CREATE OR REPLACE FUNCTION audit_knowledge_entries()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (tisch_name, aktion, datensatz_id, neue_daten, benutzer_id)
        VALUES ('knowledge_entries', TG_OP, NEW.id, to_jsonb(NEW), NEW.created_by);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (tisch_name, aktion, datensatz_id, alte_daten, neue_daten, benutzer_id)
        VALUES ('knowledge_entries', TG_OP, NEW.id, to_jsonb(OLD), to_jsonb(NEW), NEW.updated_by);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (tisch_name, aktion, datensatz_id, alte_daten, benutzer_id)
        VALUES ('knowledge_entries', TG_OP, OLD.id, to_jsonb(OLD), NULL);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_knowledge_entries_audit
    AFTER INSERT OR UPDATE OR DELETE ON knowledge_entries
    FOR EACH ROW
    EXECUTE FUNCTION audit_knowledge_entries();

-- ============================================================
-- COMMENTS for documentation
-- ============================================================

COMMENT ON TABLE knowledge_entries IS 'Main table for medical knowledge articles';
COMMENT ON COLUMN knowledge_entries.search_vector IS 'Tsvector for full-text search, auto-generated from titel, zusammenfassung, inhalt';
COMMENT ON COLUMN knowledge_entries.dokumenttyp IS 'Document type: Leitlinie, SOP, Studie, etc.';
COMMENT ON TABLE audit_log IS 'Compliance audit trail for all changes to knowledge_entries';


-- v_entry_search (faceted search view) was removed 2026-09-01; keyword search
-- queries knowledge_entries directly. Drop it on existing installations:
--   DROP VIEW IF EXISTS v_entry_search CASCADE;
