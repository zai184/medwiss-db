"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict



# =============================================================================
# Entry-related Enums
# =============================================================================


class EntrySchwierigkeit(str, Enum):
    """Difficulty level of an entry."""

    GRUNDLEGEND = "grundlegend"
    ANFAENGER = "anfaenger"
    FORTGESCHRITTEN = "fortgeschritten"
    EXPERTE = "experte"


# =============================================================================
# Entry-related Models
# =============================================================================


class FachgebietResponse(BaseModel):
    """Response model for a specialty/field."""

    id: int
    name: str
    beschreibung: Optional[str] = None
    needs_review: bool = False
    source: str = "seed"

    model_config = ConfigDict(from_attributes=True)


class DiagnoseResponse(BaseModel):
    """Response model for a diagnosis."""

    id: int
    code: str
    name: str
    beschreibung: Optional[str] = None
    needs_review: bool = False
    source: str = "seed"

    model_config = ConfigDict(from_attributes=True)


class DokumenttypResponse(BaseModel):
    """Response model for a document type."""

    id: int
    name: str
    needs_review: bool = False
    source: str = "seed"

    model_config = ConfigDict(from_attributes=True)


class OrdnerLabelResponse(BaseModel):
    """Response model for a folder label."""

    id: int
    name: str
    needs_review: bool = False
    source: str = "seed"

    model_config = ConfigDict(from_attributes=True)


class DokumenttypCreate(BaseModel):
    """Schema for creating a Dokumenttyp."""

    name: str


class DokumenttypUpdate(BaseModel):
    """Schema for renaming a Dokumenttyp."""

    name: str


class OrdnerLabelCreate(BaseModel):
    """Schema for creating an OrdnerLabel."""

    name: str


class OrdnerLabelUpdate(BaseModel):
    """Schema for renaming an OrdnerLabel."""

    name: str


class SymptomResponse(BaseModel):
    """Response model for a symptom."""

    id: int
    name: str
    beschreibung: Optional[str] = None
    needs_review: bool = False
    source: str = "seed"

    model_config = ConfigDict(from_attributes=True)


class EntryBase(BaseModel):
    """Base model for knowledge entries."""

    titel: str = Field(..., min_length=1, max_length=500)
    zusammenfassung: Optional[str] = None
    inhalt: str = Field(..., min_length=1)
    quelle: Optional[str] = Field(None, max_length=500)
    schwierigkeit: Optional[str] = None
    unterkategorie: Optional[str] = Field(None, max_length=100, description="Subfolder name (e.g., Notaufnahme, Kardio, Gyn)")
    dokumenttyp: Optional[str] = Field(None, max_length=50, description="Document type (Leitlinie, SOP, Studie, …)")
    dokumenttyp_id: Optional[int] = None
    source_hierarchy: list[str] = Field(default_factory=list, description="Folder-derived labels")
    source_path: Optional[str] = None
    file_hash: Optional[str] = Field(None, max_length=64, description="SHA-256 hash of source file")

    model_config = ConfigDict(from_attributes=True)


class EntryCreate(EntryBase):
    """Model for creating a new knowledge entry."""

    fachgebiet_ids: list[int] = []
    diagnose_ids: list[int] = []
    symptom_ids: list[int] = []
    ordner_label_ids: list[int] = []


class EntryUpdate(BaseModel):
    """Model for updating an existing knowledge entry."""

    titel: Optional[str] = Field(None, min_length=1, max_length=500)
    zusammenfassung: Optional[str] = None
    inhalt: Optional[str] = Field(None, min_length=1)
    quelle: Optional[str] = Field(None, max_length=500)
    schwierigkeit: Optional[str] = None
    unterkategorie: Optional[str] = Field(None, max_length=100, description="Subfolder name (e.g., Notaufnahme, Kardio, Gyn)")
    dokumenttyp: Optional[str] = Field(None, max_length=50)
    source_hierarchy: Optional[list[str]] = None
    fachgebiet_ids: Optional[list[int]] = None
    diagnose_ids: Optional[list[int]] = None
    symptom_ids: Optional[list[int]] = None
    ordner_label_ids: Optional[list[int]] = None
    dokumenttyp_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class EntryResponse(EntryBase):
    """Response model for a knowledge entry."""

    id: int
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    fachgebiete: list[FachgebietResponse] = []
    diagnosen: list[DiagnoseResponse] = []
    symptome: list[SymptomResponse] = []
    dokumenttyp_ref: Optional[DokumenttypResponse] = None
    ordner_labels: list[OrdnerLabelResponse] = []

    model_config = ConfigDict(from_attributes=True)


class EntryListResponse(BaseModel):
    """Response model for a paginated list of entries."""

    items: list[EntryResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


class TagSuggestionItem(BaseModel):
    """A single folder-derived Fachgebiet suggestion."""

    label: str
    id: Optional[int] = None
    already_linked: bool = False


class EntryTagSuggestionsResponse(BaseModel):
    """Folder-path tag suggestions for an entry."""

    source_path: Optional[str] = None
    unterkategorie: Optional[str] = None
    dokumenttyp: Optional[str] = None
    stored_dokumenttyp: Optional[str] = None
    hierarchy_labels: list[str] = []
    stored_hierarchy: list[str] = []
    missing_hierarchy: list[str] = []
    fachgebiete: list[TagSuggestionItem] = []
    has_actionable_suggestions: bool = False


class ResolveLabelsRequest(BaseModel):
    """Resolve string labels to lookup IDs (creates missing rows)."""

    fachgebiete: list[str] = []
    diagnosen: list[dict | str] = []
    symptome: list[str] = []
    dokumenttyp: Optional[str] = None
    ordner_labels: list[str] = []


class ResolveLabelsResponse(BaseModel):
    """Resolved lookup IDs from string labels."""

    fachgebiet_ids: list[int] = []
    diagnose_ids: list[int] = []
    symptom_ids: list[int] = []
    needs_review_count: int = 0
    dokumenttyp_id: Optional[int] = None
    ordner_label_ids: list[int] = []



# =============================================================================
# Search-related Models
# =============================================================================


class SearchResultItem(BaseModel):
    """Single search result with relevance information."""

    id: int
    titel: str
    zusammenfassung: Optional[str] = None
    inhalt: Optional[str] = None
    dokumenttyp: Optional[str] = None
    schwierigkeit: Optional[str] = None
    unterkategorie: Optional[str] = Field(None, max_length=100, description="Subfolder name (e.g., Notaufnahme, Kardio, Gyn)")
    source_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    rank: float  # tier score: title (3) > filename (2) > folder (1.5) > content (1)

    model_config = ConfigDict(from_attributes=True)



class FilterOption(BaseModel):
    """A filter option (id + display name + matching entry count)."""

    id: int
    name: str
    count: int = 0


class FolderOption(BaseModel):
    """A top-level source folder segment with its entry count."""

    name: str
    count: int


class SearchFilterOptions(BaseModel):
    """Available filter options for the search page facet sidebar."""

    fachgebiete: list[FilterOption] = []
    diagnosen: list[FilterOption] = []
    symptome: list[FilterOption] = []
    dokumenttypen: list[FilterOption] = []
    ordner_labels: list[FilterOption] = []
    folders: list[FolderOption] = []


class SearchResponse(BaseModel):
    """Response model for search queries."""

    items: list[SearchResultItem]
    total: int
    limit: int
    offset: int
    query: str
    filters: Optional[SearchFilterOptions] = None

    model_config = ConfigDict(from_attributes=True)


# Chunk Search (AWMF) Models
# =============================================================================


class ChunkResultItem(BaseModel):
    """A single AWMF chunk-search hit (passage-level, not an entry)."""

    id: int
    source_type: str
    source_path: str
    title: str
    awmf: Optional[str] = None
    society: Optional[str] = None
    page: Optional[int] = None
    seq: int
    text: str
    document_id: int
    score: float

    model_config = ConfigDict(from_attributes=True)


class ChunkSearchResponse(BaseModel):
    """Response model for AWMF chunk search."""

    items: list[ChunkResultItem]
    total: int
    limit: int
    offset: int
    query: str

    model_config = ConfigDict(from_attributes=True)


class RagSourceItem(BaseModel):
    """A retrieved passage cited by a RAG answer (no raw text — too large)."""

    id: int
    source_path: str
    title: str
    awmf: Optional[str] = None
    society: Optional[str] = None
    page: Optional[int] = None
    score: float

    model_config = ConfigDict(from_attributes=True)


class RagResponse(BaseModel):
    """Response model for RAG over AWMF chunks."""

    answer: str
    sources: list[RagSourceItem]
    query: str
    model: str

    model_config = ConfigDict(from_attributes=True)
# Pipeline-related Models
# =============================================================================




class PipelineResult(BaseModel):
    """Response model for pipeline file processing."""

    success: bool = Field(..., description="Whether processing succeeded")
    file_type: str = Field(..., description="Detected file type (image, audio, text)")
    extracted_text: str = Field(default="", description="Extracted text content")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

    model_config = ConfigDict(from_attributes=True)




# =============================================================================
# Summarize Models
# =============================================================================


class SummarizeRequest(BaseModel):
    """Request model for text extraction and summarization."""

    skill: Literal["studie", "leitlinie", "screenshot", "standard"] = Field(
        ..., description="Type of content to process"
    )
    provider: str = Field(default="llamaserver", description="AI provider to use")
    model: Optional[str] = Field(None, description="Specific model to use (provider-dependent)")

    model_config = ConfigDict(from_attributes=True)


class SummarizeResponse(BaseModel):
    """Response model for text extraction and summarization."""

    success: bool = Field(..., description="Whether processing succeeded")
    extracted_text: str = Field(default="", description="Extracted text content")
    summary: str = Field(default="", description="Generated summary")
    model_used: Optional[str] = Field(None, description="Model used for processing")
    skill_used: str = Field(..., description="Skill type used for processing")

    model_config = ConfigDict(from_attributes=True)


class TranscribeRequest(BaseModel):
    """Request model for pure OCR transcription (no LLM)."""

    backend: Optional[str] = Field(
        None,
        description="OCR backend to use: tesseract, openrouter-vision. "
        "None = run the configured OCR_BACKENDS seam in order (auto).",
    )

    model_config = ConfigDict(from_attributes=True)


class TranscribeResponse(BaseModel):
    """Response model for pure OCR transcription (no LLM)."""

    success: bool = Field(..., description="Whether processing succeeded")
    extracted_text: str = Field(default="", description="Extracted raw text content")
    file_type: str = Field(..., description="Detected file type (image, audio, text)")

    model_config = ConfigDict(from_attributes=True)
