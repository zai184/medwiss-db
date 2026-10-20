import axios from 'axios';
/** Generated OpenAPI types — regenerate with `./scripts/gen-api.sh`. Do not edit api-types.d.ts. */
export type { components as ApiComponents, paths as ApiPaths } from './api-types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Types (handwritten until a call site is switched to ApiComponents['schemas'])
export interface EntryResponse {
  id: number;
  titel: string;
  zusammenfassung: string | null;
  inhalt: string;
  quelle: string | null;
  unterkategorie: string | null;
  dokumenttyp: string | null;
  dokumenttyp_id: number | null;
  dokumenttyp_ref: DokumenttypResponse | null;
  source_hierarchy: string[];
  source_path: string | null;
  file_hash: string | null;
  schwierigkeit: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
  fachgebiete: FachgebietResponse[];
  diagnosen: DiagnoseResponse[];
  symptome: SymptomResponse[];
  ordner_labels: OrdnerLabelResponse[];
}
export interface DokumenttypResponse {
  id: number;
  name: string;
  needs_review: boolean;
  source: string;
}
export interface OrdnerLabelResponse {
  id: number;
  name: string;
  needs_review: boolean;
  source: string;
}
export interface FachgebietResponse {
  id: number;
  name: string;
  beschreibung: string | null;
}

export interface DiagnoseResponse {
  id: number;
  code: string;
  name: string;
  beschreibung: string | null;
  icd11_code?: string | null;
}
export interface SymptomResponse {
  id: number;
  name: string;
  beschreibung: string | null;
}

export interface EntryListResponse {
  items: EntryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface StatsOverview {
  total_entries: number;
  entries_by_category: Record<string, number>;
  recent_entries: EntryResponse[];
}

export interface CategoryStats {
  category: string;
  count: number;
  percentage: number;
}

export interface FachStats {
  fachgebiet_id: number;
  fachgebiet_name: string;
  count: number;
}

export interface DiagnoseStats {
  diagnose_id: number;
  diagnose_name: string;
  diagnose_code: string;
  count: number;
}

// Stats API
export const statsApi = {
  getOverview: async (): Promise<StatsOverview> => {
    const response = await apiClient.get('/stats/overview');
    return response.data;
  },

  getByCategory: async (): Promise<CategoryStats[]> => {
    const response = await apiClient.get('/stats/by-category');
    return response.data;
  },

  getByFach: async (): Promise<FachStats[]> => {
    const response = await apiClient.get('/stats/by-fach');
    return response.data;
  },

  getByDiagnose: async (limit: number = 10): Promise<DiagnoseStats[]> => {
    const response = await apiClient.get('/stats/by-diagnose', { params: { limit } });
    return response.data;
  }
};

// File Sync API
export interface SyncResult {
  success: boolean;
  message: string;
  changes_detected: {
    new_files: number;
    modified_files: number;
    deleted_entries: number;
    imported: number;
    updated: number;
    archived: number;
  };
}

export interface SyncStatus {
  total_files: number;
  files_waiting: number;
  last_change: string | null;
  last_sync: string | null;
  running: boolean;
  imported: number;
  updated: number;
  deleted: number;
  sync_errors: string[];
  source_folders: { name: string; path: string; category: string; exists: boolean }[];
}

export const filesApi = {
  triggerSync: async (): Promise<SyncResult> => {
    const response = await apiClient.post('/files/sync');
    return response.data;
  },
  getSyncStatus: async (): Promise<SyncStatus> => {
    const response = await apiClient.get('/files/admin/sync-status');
    return response.data;
  }
};

export interface EntryCreate {
  titel: string;
  zusammenfassung: string | null;
  inhalt: string;
  quelle: string | null;
  dokumenttyp?: string | null;
  dokumenttyp_id?: number | null;
  source_hierarchy?: string[];
  schwierigkeit: string | null;
  fachgebiet_ids: number[];
  diagnose_ids: number[];
  symptom_ids: number[];
  ordner_label_ids?: number[];
}

// Entries API
export const entriesApi = {
  getAll: async (params?: { limit?: number; offset?: number; source_path?: string }): Promise<EntryListResponse> => {
    const response = await apiClient.get('/entries', { params });
    return response.data;
  },

  getRecent: async (limit: number = 5): Promise<EntryResponse[]> => {
    const response = await apiClient.get('/entries', { params: { limit, offset: 0 } });
    return response.data.items;
  },

  getById: async (id: number): Promise<EntryResponse> => {
    const response = await apiClient.get(`/entries/${id}`);
    return response.data;
  },

  create: async (entryData: EntryCreate): Promise<EntryResponse> => {
    const response = await apiClient.post('/entries', entryData);
    return response.data;
  },

  update: async (id: number, entryData: Partial<EntryCreate>): Promise<EntryResponse> => {
    const response = await apiClient.put(`/entries/${id}`, entryData);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/entries/${id}`);
  },

  getTagSuggestions: async (id: number): Promise<EntryTagSuggestionsResponse> => {
    const response = await apiClient.get(`/entries/${id}/tag-suggestions`);
    return response.data;
  },

  applyTagSuggestions: async (id: number): Promise<EntryTagSuggestionsResponse> => {
    const response = await apiClient.post(`/entries/${id}/tag-suggestions/apply`);
    return response.data;
  }
};

export interface TagSuggestionItem {
  label: string;
  id: number | null;
  already_linked: boolean;
}

export interface EntryTagSuggestionsResponse {
  source_path: string | null;
  unterkategorie: string | null;
  dokumenttyp: string | null;
  stored_dokumenttyp: string | null;
  hierarchy_labels: string[];
  stored_hierarchy: string[];
  missing_hierarchy: string[];
  fachgebiete: TagSuggestionItem[];
  has_actionable_suggestions: boolean;
}

export interface ResolveLabelsResponse {
  fachgebiet_ids: number[];
  diagnose_ids: number[];
  symptom_ids: number[];
  dokumenttyp_id: number | null;
  ordner_label_ids: number[];
  needs_review_count: number;
}

// Classifications API
export const classificationsApi = {
  getFachgebiete: async (): Promise<FachgebietResponse[]> => {
    const response = await apiClient.get('/fachgebiete');
    return response.data;
  },

  resolveLabels: async (payload: {
    fachgebiete?: string[];
    diagnosen?: ({ name: string; code?: string } | string)[];
    symptome?: string[];
    dokumenttyp?: string;
    ordner_labels?: string[];
  }): Promise<ResolveLabelsResponse> => {
    const response = await apiClient.post('/resolve-labels', payload);
    return response.data;
  },

  // --- Dokumenttypen CRUD ---
  getDokumenttypen: async (): Promise<DokumenttypResponse[]> => {
    const response = await apiClient.get('/dokumenttypen');
    return response.data;
  },
  createDokumenttyp: async (data: { name: string }): Promise<DokumenttypResponse> => {
    const response = await apiClient.post('/dokumenttypen', data);
    return response.data;
  },
  updateDokumenttyp: async (id: number, data: { name: string }): Promise<DokumenttypResponse> => {
    const response = await apiClient.put(`/dokumenttypen/${id}`, data);
    return response.data;
  },
  deleteDokumenttyp: async (id: number): Promise<void> => {
    await apiClient.delete(`/dokumenttypen/${id}`);
  },

  // --- Ordner-Labels CRUD ---
  getOrdnerLabels: async (): Promise<OrdnerLabelResponse[]> => {
    const response = await apiClient.get('/ordner-labels');
    return response.data;
  },
  createOrdnerLabel: async (data: { name: string }): Promise<OrdnerLabelResponse> => {
    const response = await apiClient.post('/ordner-labels', data);
    return response.data;
  },
  updateOrdnerLabel: async (id: number, data: { name: string }): Promise<OrdnerLabelResponse> => {
    const response = await apiClient.put(`/ordner-labels/${id}`, data);
    return response.data;
  },
  deleteOrdnerLabel: async (id: number): Promise<void> => {
    await apiClient.delete(`/ordner-labels/${id}`);
  },
  getDiagnosen: async (): Promise<DiagnoseResponse[]> => {
    const response = await apiClient.get('/diagnosen');
    return response.data;
  },

  getSymptome: async (): Promise<SymptomResponse[]> => {
    const response = await apiClient.get('/symptome');
    return response.data;
  },


  // --- Fachgebiete CRUD ---
  createFachgebiet: async (data: { name: string; beschreibung?: string | null }): Promise<FachgebietResponse> => {
    const response = await apiClient.post('/fachgebiete', data);
    return response.data;
  },
  updateFachgebiet: async (id: number, data: { name?: string; beschreibung?: string | null }): Promise<FachgebietResponse> => {
    const response = await apiClient.put(`/fachgebiete/${id}`, data);
    return response.data;
  },
  deleteFachgebiet: async (id: number): Promise<void> => {
    await apiClient.delete(`/fachgebiete/${id}`);
  },

  // --- Diagnosen CRUD ---
  createDiagnose: async (data: { code: string; name: string; beschreibung?: string | null }): Promise<DiagnoseResponse> => {
    const response = await apiClient.post('/diagnosen', data);
    return response.data;
  },
  updateDiagnose: async (id: number, data: { code?: string; name?: string; beschreibung?: string | null }): Promise<DiagnoseResponse> => {
    const response = await apiClient.put(`/diagnosen/${id}`, data);
    return response.data;
  },
  deleteDiagnose: async (id: number): Promise<void> => {
    await apiClient.delete(`/diagnosen/${id}`);
  },

  // --- Symptome CRUD ---
  createSymptom: async (data: { name: string; beschreibung?: string | null }): Promise<SymptomResponse> => {
    const response = await apiClient.post('/symptome', data);
    return response.data;
  },
  updateSymptom: async (id: number, data: { name?: string; beschreibung?: string | null }): Promise<SymptomResponse> => {
    const response = await apiClient.put(`/symptome/${id}`, data);
    return response.data;
  },
  deleteSymptom: async (id: number): Promise<void> => {
    await apiClient.delete(`/symptome/${id}`);
  }
};



export interface SearchResultItem {
  id: number;
  titel: string;
  zusammenfassung: string | null;
  dokumenttyp: string | null;
  schwierigkeit: string | null;
  rank: number;
  match_type: string;
  fachgebiete: FachgebietResponse[];
  diagnosen: DiagnoseResponse[];
  symptome: SymptomResponse[];
}

export interface SearchResponse {
  items: SearchResultItem[];
  total: number;
  limit: number;
  offset: number;
  query: string;
  search_type: string;
}

// Chunk (AWMF) Search API
export interface ChunkResultItem {
  id: number;
  source_type: string;
  source_path: string;
  title: string;
  awmf: string | null;
  society: string | null;
  page: number | null;
  seq: number;
  text: string;
  document_id: number;
  score: number;
}

export interface ChunkSearchResponse {
  items: ChunkResultItem[];
  total: number;
  limit: number;
  offset: number;
  query: string;
}

export const chunkSearchApi = {
  search: async (
    query: string,
    params?: { limit?: number; offset?: number }
  ): Promise<ChunkSearchResponse> => {
    const response = await apiClient.get('/search/chunks', {
      params: { q: query, ...params }
    });
    return response.data;
  }
};

export interface RagSourceItem {
  id: number;
  source_path: string;
  title: string;
  awmf: string | null;
  society: string | null;
  page: number | null;
  score: number;
}

export interface RagResponse {
  answer: string;
  sources: RagSourceItem[];
  query: string;
  model: string;
}

export const ragApi = {
  answer: async (query: string, top_k = 6): Promise<RagResponse> => {
    const response = await apiClient.get('/search/chunks/rag', {
      params: { q: query, top_k }
    });
    return response.data;
  }
};

// Sources API
export interface SourceInfo {
  name: string;
  display_name: string;
  category: string;
  description: string;
  file_types: string[];
  default_fachgebiete: string[];
  subcategories: string[];
}

export const sourcesApi = {
  getSources: async (): Promise<SourceInfo[]> => {
    const response = await apiClient.get('/sources');
    return response.data;
  },

  getAll: async (): Promise<SourceInfo[]> => {
    const response = await apiClient.get('/sources');
    return response.data;
  }
};

// Pipeline API
export interface PipelineResult {
  success: boolean;
  file_type: string;
  extracted_text: string;
  processing_time_ms: number;
}

export const pipelineApi = {
  processFile: async (file: File): Promise<PipelineResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/pipeline/process-file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }
};

// Admin API
export interface ClassifyFromFilenameResult {
  total_entries: number;
  fachgebiete_assigned: number;
  diagnosen_assigned: number;
  symptome_assigned: number;
  entries_touched: number;
  icd11_enriched: number;
  dry_run: boolean;
}

export interface ClassifyProgressEvent {
  batch: number;
  total_batches: number;
  entries_in_batch: number;
  keywords_found: number;
  status: string;
  error?: string;
}

export const adminApi = {
  classifyFromFilename: async (opts: {
    force?: boolean;
    dry_run?: boolean;
    limit?: number;
  }): Promise<ClassifyFromFilenameResult> => {
    const resp = await fetch('/api/v1/admin/classify-from-filename', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force: opts.force ?? false,
        dry_run: opts.dry_run ?? true,
        limit: opts.limit,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const text = await resp.text();
    // Parse final SSE "done" event from the stream
    const doneMatch = text.match(/event: done\ndata: ({.*})/);
    if (doneMatch) return JSON.parse(doneMatch[1]);
    const errMatch = text.match(/event: error\ndata: ({.*})/);
    if (errMatch) throw new Error(JSON.parse(errMatch[1]).message);
    throw new Error('No result received');
  },

  /** Stream classification — yields progress events via callback, returns final result. */
  classifyFromFilenameStream: async (
    opts: { force?: boolean; dry_run?: boolean; limit?: number },
    onBatch: (evt: ClassifyProgressEvent) => void,
    onStart?: (info: { force: boolean; dry_run: boolean; limit?: number }) => void,
    onError?: (msg: string) => void,
  ): Promise<ClassifyFromFilenameResult> => {
    const resp = await fetch('/api/v1/admin/classify-from-filename', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        force: opts.force ?? false,
        dry_run: opts.dry_run ?? true,
        limit: opts.limit,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const reader = resp.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result: ClassifyFromFilenameResult | null = null;

    function processBuffer() {
      const events = buffer.split('\n\n');
      buffer = events.pop()!; // keep incomplete tail
      for (const event of events) {
        const lines = event.split('\n');
        let eventType = '';
        let data = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7);
          if (line.startsWith('data: ')) data = line.slice(6);
        }
        if (!eventType || !data) continue;
        try {
          const parsed = JSON.parse(data);
          if (eventType === 'start' && onStart) onStart(parsed);
          else if (eventType === 'batch') onBatch(parsed);
          else if (eventType === 'done') result = parsed;
          else if (eventType === 'error' && onError) onError(parsed.message);
        } catch { /* skip malformed */ }
      }
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      processBuffer();
    }
    // Flush remaining buffer
    if (buffer.trim()) processBuffer();

    if (!result) throw new Error('No result received');
    return result;
  },
};

// References API
export interface ReferenceLink {
  label: string;
  url: string;
}

export interface ReferenceSubSection {
  title: string | null;
  links: ReferenceLink[];
}

export interface ReferenceSection {
  title: string;
  sub: ReferenceSubSection[];
}

export const referencesApi = {
  getReferences: async (): Promise<ReferenceSection[]> => {
    const resp = await apiClient.get('/references');
    return resp.data;
  },
};

// PubMed API
export interface PubmedResult {
  pmid: string;
  title: string;
  authors: string[];
  journal: string;
  date: string;
  doi: string | null;
  url: string;
  abstract: string | null;
}

export interface PubmedSearchResponse {
  total: number;
  results: PubmedResult[];
  query: string;
}

export interface PubmedSearchFilters {
  q?: string;
  title?: string;
  author?: string;
  ptype?: string;
  publisher?: string;
  date_preset?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
}
export const pubmedApi = {
  search: async (filters: PubmedSearchFilters, limit = 10, offset = 0): Promise<PubmedSearchResponse> => {
    const resp = await apiClient.get('/pubmed/search', {
      params: { ...filters, limit, offset },
    });
    return resp.data;
  },
};
