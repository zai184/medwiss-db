"""Business logic for knowledge entry CRUD operations.
Extracted from api/routers/entries.py to separate concerns:
routers handle HTTP; services handle business logic + data access.
"""

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.config import settings
from api.models import (
    DiagnoseResponse,
    DokumenttypResponse,
    EntryCreate,
    EntryListResponse,
    EntryResponse,
    EntryTagSuggestionsResponse,
    EntryUpdate,
    FachgebietResponse,
    OrdnerLabelResponse,
    SymptomResponse,
    TagSuggestionItem,
)
from api.services.hierarchy_labels import (
    apply_folder_suggestions,
    extract_tag_suggestions_for_entry,
)
from config import get_content_root
from database.models import Diagnose, Dokumenttyp, Fachgebiet, KnowledgeEntry, OrdnerLabel, Symptom
from pipeline.batch_processor import calculate_file_hash
from pipeline.classification_resolver import resolve_dokumenttyp
from search.keyword import like_pattern


TEXT_SUFFIXES = {".md", ".txt", ".rst"}


def write_through(
    path: Path,
    new_text: str,
    expected_hash: Optional[str],
    content_root: Path,
) -> str:
    """Write ``new_text`` back to a text source file unless it has drifted.

    Optimistic lock: if the file exists on disk with a different SHA-256 than
    ``expected_hash`` (the entry's stored hash), raise ValueError — a file
    change has been ingested since the entry was loaded. Writes atomically
    (tmp sibling + ``os.replace``) and returns the new file SHA-256.

    Raises ValueError if ``path`` resolves outside ``content_root``.
    """
    resolved = path.resolve()
    try:
        resolved.relative_to(Path(content_root).resolve())
    except ValueError:
        raise ValueError(
            f"Refusing to write file outside content root: {resolved}"
        ) from None

    if resolved.exists() and expected_hash is not None:
        if calculate_file_hash(resolved) != expected_hash:
            raise ValueError(
                "File changed on disk since last sync — reload the entry before saving"
            )

    tmp = resolved.with_suffix(resolved.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, resolved)
    return calculate_file_hash(resolved)


class EntryService:
    """Service for knowledge entry CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    # -- Query helpers -------------------------------------------------------

    def _base_query(self):
        """Base query with relationship eager-loading."""
        return self.db.query(KnowledgeEntry).options(
            joinedload(KnowledgeEntry.fachgebiete),
            joinedload(KnowledgeEntry.diagnosen),
            joinedload(KnowledgeEntry.symptome),
            joinedload(KnowledgeEntry.dokumenttyp_ref),
            joinedload(KnowledgeEntry.ordner_labels),
        )

    def _get_or_404(self, entry_id: int) -> KnowledgeEntry:
        """Get entry by ID or raise ValueError (caller wraps as HTTPException)."""
        entry = self._base_query().filter(KnowledgeEntry.id == entry_id).first()
        if not entry:
            raise ValueError(f"Knowledge entry with ID {entry_id} not found")
        return entry

    @staticmethod
    def to_response(entry: KnowledgeEntry) -> EntryResponse:
        """Convert a KnowledgeEntry ORM object to an EntryResponse Pydantic model."""
        return EntryResponse(
            id=entry.id,
            titel=entry.titel,
            zusammenfassung=entry.zusammenfassung,
            inhalt=entry.inhalt,
            quelle=entry.quelle,
            unterkategorie=entry.unterkategorie,
            dokumenttyp=entry.dokumenttyp,
            dokumenttyp_id=entry.dokumenttyp_id,
            source_hierarchy=list(entry.source_hierarchy or []),
            schwierigkeit=entry.schwierigkeit,
            source_path=entry.source_path,
            file_hash=entry.file_hash,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            created_by=entry.created_by,
            updated_by=entry.updated_by,
            fachgebiete=[
                FachgebietResponse(
                    id=f.id,
                    name=f.name,
                    beschreibung=f.beschreibung,
                    needs_review=getattr(f, "needs_review", False),
                    source=getattr(f, "source", "seed"),
                )
                for f in entry.fachgebiete
            ],
            diagnosen=[
                DiagnoseResponse(
                    id=d.id,
                    code=d.code,
                    name=d.name,
                    beschreibung=d.beschreibung,
                    needs_review=getattr(d, "needs_review", False),
                    source=getattr(d, "source", "seed"),
                )
                for d in entry.diagnosen
            ],
            symptome=[
                SymptomResponse(
                    id=s.id,
                    name=s.name,
                    beschreibung=s.beschreibung,
                    needs_review=getattr(s, "needs_review", False),
                    source=getattr(s, "source", "seed"),
                )
                for s in entry.symptome
            ],
            dokumenttyp_ref=(
                DokumenttypResponse(
                    id=entry.dokumenttyp_ref.id,
                    name=entry.dokumenttyp_ref.name,
                    needs_review=entry.dokumenttyp_ref.needs_review,
                    source=entry.dokumenttyp_ref.source,
                )
                if entry.dokumenttyp_ref
                else None
            ),
            ordner_labels=[
                OrdnerLabelResponse(
                    id=o.id,
                    name=o.name,
                    needs_review=o.needs_review,
                    source=o.source,
                )
                for o in entry.ordner_labels
            ],
        )

    @staticmethod
    def _suggestions_response(data: dict) -> EntryTagSuggestionsResponse:
        return EntryTagSuggestionsResponse(
            source_path=data.get("source_path"),
            unterkategorie=data.get("unterkategorie"),
            dokumenttyp=data.get("dokumenttyp"),
            stored_dokumenttyp=data.get("stored_dokumenttyp"),
            hierarchy_labels=data.get("hierarchy_labels", []),
            stored_hierarchy=data.get("stored_hierarchy", []),
            missing_hierarchy=data.get("missing_hierarchy", []),
            fachgebiete=[TagSuggestionItem(**item) for item in data.get("fachgebiete", [])],
            has_actionable_suggestions=data.get("has_actionable_suggestions", False),
        )

    # -- CRUD ----------------------------------------------------------------

    def list_entries(
        self,
        limit: int = 20,
        offset: int = 0,
        dokumenttyp: Optional[str] = None,
        dokumenttypen: Optional[list[str]] = None,
        schwierigkeit: Optional[str] = None,
        fach: Optional[list[str]] = None,
        diagnose: Optional[list[str]] = None,
        symptom: Optional[list[str]] = None,
        source_path: Optional[str] = None,
    ) -> EntryListResponse:
        """Get a paginated list of knowledge entries with optional filters."""
        query = self._base_query()

        if dokumenttyp:
            query = query.filter(KnowledgeEntry.dokumenttyp == dokumenttyp)
        if dokumenttypen:
            query = query.filter(KnowledgeEntry.dokumenttyp.in_(dokumenttypen))
        if schwierigkeit:
            query = query.filter(KnowledgeEntry.schwierigkeit == schwierigkeit)
        if fach:
            for fach_name in fach:
                # Match real junction links OR folder-derived source_hierarchy,
                # mirroring v_entry_search.fachgebiete_names semantics.
                query = query.filter(
                    or_(
                        KnowledgeEntry.fachgebiete.any(Fachgebiet.name == fach_name),
                        KnowledgeEntry.source_hierarchy.contains([fach_name]),
                    )
                )
        if diagnose:
            for diag_name in diagnose:
                query = query.filter(KnowledgeEntry.diagnosen.any(Diagnose.name == diag_name))
        if symptom:
            for sym_name in symptom:
                query = query.filter(KnowledgeEntry.symptome.any(Symptom.name == sym_name))
        if source_path:
            query = query.filter(
                KnowledgeEntry.source_path.like(like_pattern(source_path), escape="\\")
            )

        total = query.count()
        entries = query.offset(offset).limit(limit).all()

        return EntryListResponse(
            items=[self.to_response(entry) for entry in entries],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_entry(self, entry_id: int) -> EntryResponse:
        """Get a single knowledge entry by ID."""
        entry = self._get_or_404(entry_id)
        return self.to_response(entry)

    def get_tag_suggestions(self, entry_id: int) -> EntryTagSuggestionsResponse:
        """Get folder-path tag suggestions for an entry."""
        entry = self._get_or_404(entry_id)
        return self._suggestions_response(extract_tag_suggestions_for_entry(self.db, entry))

    def apply_tag_suggestions(self, entry_id: int) -> EntryTagSuggestionsResponse:
        """Apply missing folder hierarchy labels to entry metadata."""
        entry = self._get_or_404(entry_id)
        apply_folder_suggestions(self.db, entry)
        self.db.refresh(entry)
        return self._suggestions_response(extract_tag_suggestions_for_entry(self.db, entry))

    def create_entry(self, entry_data: EntryCreate, user_id: int) -> EntryResponse:
        """Create a new knowledge entry with junction relationships."""
        db_entry = KnowledgeEntry(
            titel=entry_data.titel,
            zusammenfassung=entry_data.zusammenfassung,
            inhalt=entry_data.inhalt,
            quelle=entry_data.quelle,
            dokumenttyp=entry_data.dokumenttyp,
            schwierigkeit=entry_data.schwierigkeit,
            created_by=user_id,
            updated_by=user_id,
        )

        # Unified tagging: dokumenttyp_id wins over the legacy string (dual-write).
        if entry_data.dokumenttyp_id is not None:
            typ = (
                self.db.query(Dokumenttyp)
                .filter(Dokumenttyp.id == entry_data.dokumenttyp_id)
                .first()
            )
            if typ is None:
                raise ValueError(
                    f"Dokumenttyp with ID {entry_data.dokumenttyp_id} not found"
                )
            db_entry.dokumenttyp_id = typ.id
            db_entry.dokumenttyp = typ.name  # dual-write legacy string


        self.db.add(db_entry)
        self.db.flush()

        if entry_data.fachgebiet_ids:
            fachgebiete = (
                self.db.query(Fachgebiet)
                .filter(Fachgebiet.id.in_(entry_data.fachgebiet_ids))
                .all()
            )
            db_entry.fachgebiete = fachgebiete

        if entry_data.diagnose_ids:
            diagnosen = (
                self.db.query(Diagnose)
                .filter(Diagnose.id.in_(entry_data.diagnose_ids))
                .all()
            )
            db_entry.diagnosen = diagnosen

        if entry_data.symptom_ids:
            symptome = (
                self.db.query(Symptom)
                .filter(Symptom.id.in_(entry_data.symptom_ids))
                .all()
            )
            db_entry.symptome = symptome

        if entry_data.ordner_label_ids:
            labels = (
                self.db.query(OrdnerLabel)
                .filter(OrdnerLabel.id.in_(entry_data.ordner_label_ids))
                .all()
            )
            db_entry.ordner_labels = labels
            # dual-write mirror into legacy source_hierarchy
            db_entry.source_hierarchy = sorted(o.name for o in labels)


        self.db.commit()
        self.db.refresh(db_entry)

        # Reload with relationships
        db_entry = self._base_query().filter(KnowledgeEntry.id == db_entry.id).first()
        return self.to_response(db_entry)

    def update_entry(self, entry_id: int, entry_data: EntryUpdate, user_id: int) -> EntryResponse:
        """Update an existing knowledge entry."""
        entry = self._get_or_404(entry_id)

        update_data = entry_data.model_dump(exclude_unset=True)
        fachgebiet_ids = update_data.pop("fachgebiet_ids", None)
        diagnose_ids = update_data.pop("diagnose_ids", None)
        symptom_ids = update_data.pop("symptom_ids", None)
        dokumenttyp_id = update_data.pop("dokumenttyp_id", None)
        ordner_label_ids = update_data.pop("ordner_label_ids", None)

        dokumenttyp_id_set = "dokumenttyp_id" in entry_data.model_dump(exclude_unset=True)

        # File write-through: a text-backed entry whose inhalt changed is
        # written back to its source file, keeping disk and DB in sync (the
        # file is otherwise re-ingested and silently overwrites the DB edit).
        new_inhalt = update_data.get("inhalt")
        if (
            settings.file_writeback_enabled
            and new_inhalt is not None
            and new_inhalt != entry.inhalt
            and entry.source_path
            and Path(entry.source_path).suffix.lower() in TEXT_SUFFIXES
        ):
            entry.file_hash = write_through(
                Path(entry.source_path),
                new_inhalt,
                entry.file_hash,
                get_content_root(),
            )

        for field, value in update_data.items():
            setattr(entry, field, value)

        entry.version += 1
        entry.updated_by = user_id

        if fachgebiet_ids is not None:
            fachgebiete = (
                self.db.query(Fachgebiet).filter(Fachgebiet.id.in_(fachgebiet_ids)).all()
            )
            entry.fachgebiete = fachgebiete

        if diagnose_ids is not None:
            diagnosen = (
                self.db.query(Diagnose).filter(Diagnose.id.in_(diagnose_ids)).all()
            )
            entry.diagnosen = diagnosen

        if symptom_ids is not None:
            symptome = (
                self.db.query(Symptom).filter(Symptom.id.in_(symptom_ids)).all()
            )
            entry.symptome = symptome

        if dokumenttyp_id is not None:
            typ = self.db.query(Dokumenttyp).filter(Dokumenttyp.id == dokumenttyp_id).first()
            if typ is None:
                raise ValueError(f"Dokumenttyp with ID {dokumenttyp_id} not found")
            entry.dokumenttyp_id = typ.id
            entry.dokumenttyp = typ.name  # dual-write legacy string
        elif "dokumenttyp" in update_data:
            # Rename-sync: legacy string write → resolve to ID (dual-write).
            name = update_data["dokumenttyp"]
            if name:
                entry.dokumenttyp_id = resolve_dokumenttyp(
                    self.db, name, source="manual"
                ).id
            else:
                entry.dokumenttyp_id = None
        elif dokumenttyp_id_set and dokumenttyp_id is None:
            # Explicit dokumenttyp_id: null → clear both ID and legacy string.
            entry.dokumenttyp = None
        if ordner_label_ids is not None:
            labels = (
                self.db.query(OrdnerLabel).filter(OrdnerLabel.id.in_(ordner_label_ids)).all()
                if ordner_label_ids
                else []
            )
            entry.ordner_labels = labels
            # dual-write mirror into legacy source_hierarchy
            entry.source_hierarchy = sorted(o.name for o in labels)


        self.db.commit()
        self.db.refresh(entry)

        entry = self._base_query().filter(KnowledgeEntry.id == entry_id).first()
        return self.to_response(entry)

    def delete_entry(self, entry_id: int) -> None:
        """Delete a knowledge entry."""
        entry = self._get_or_404(entry_id)
        self.db.delete(entry)
        self.db.commit()

    def get_dokumenttypen(self) -> list[str]:
        """Get all dokumenttyp names from the lookup table (SoT)."""
        rows = self.db.query(Dokumenttyp.name).order_by(Dokumenttyp.name).all()
        return [r[0] for r in rows]
