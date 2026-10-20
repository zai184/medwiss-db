"""Unified tagging service with pluggable strategies.

Strategies:
- FolderHierarchy: derived labels → source_hierarchy, unterkategorie, dokumenttyp
- Manual: explicit ID assignment from user selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from api.services.hierarchy_labels import (
    CATEGORY_LABELS,
    extract_hierarchical_labels,
    find_source_for_file,
)
from config import SourceConfig
from database.models import (
    Diagnose,
    Fachgebiet,
    KnowledgeEntry,
    OrdnerLabel,
    Symptom,
)
from pipeline.classification_resolver import (
    ResolutionResult,
    resolve_classifications,
    resolve_diagnose,
    resolve_dokumenttyp,
    resolve_fachgebiet,
    resolve_ordner_label,
    resolve_symptom,
)

logger = logging.getLogger(__name__)


class TagDimension(str, Enum):
    FACHGEBIET = "fachgebiet"
    DIAGNOSE = "diagnose"
    SYMPTOM = "symptom"
    HIERARCHY = "hierarchy"
    DOKUMENTTYP = "dokumenttyp"


class TagSource(str, Enum):
    SEED = "seed"
    LLM = "llm"
    FOLDER = "folder"
    MANUAL = "manual"


@dataclass
class TagProposal:
    dimension: TagDimension
    label: str
    source: TagSource
    id: Optional[int] = None
    code: Optional[str] = None
    needs_review: bool = False


@dataclass
class ApplyResult:
    hierarchy_added: int = 0
    fachgebiete_added: int = 0
    diagnosen_added: int = 0
    symptome_added: int = 0
    dokumenttyp_set: bool = False
    needs_review_count: int = 0


class FolderHierarchyStrategy:
    """Derive folder labels as entry metadata (not M2M fachgebiet rows)."""

    def propose(
        self,
        file_path: Path | str,
        source: SourceConfig,
        source_root: Path,
    ) -> list[TagProposal]:
        labels, unterkategorie = extract_hierarchical_labels(file_path, source, source_root)
        if not labels and unterkategorie:
            labels = [unterkategorie]
        dokumenttyp = CATEGORY_LABELS.get(source.category, source.category)
        proposals: list[TagProposal] = [
            TagProposal(
                dimension=TagDimension.DOKUMENTTYP,
                label=dokumenttyp,
                source=TagSource.FOLDER,
            ),
        ]
        for i, label in enumerate(labels):
            proposals.append(
                TagProposal(
                    dimension=TagDimension.HIERARCHY,
                    label=label,
                    source=TagSource.FOLDER,
                )
            )
            # For specialty folders (5_Fächer), derive the Fachgebiet from the
            # top-level specialty subfolder - no AI classification needed.
            # Only the first path segment is the specialty (e.g. "Kardiologie");
            # deeper segments (topic/author subfolders) must not become tags.
            # Skip the synthetic category-name fallback (loose files in the
            # source root have no specialty).
            if (
                source.category == "faecher"
                and i == 0
                and label != CATEGORY_LABELS.get(source.category, source.category)
            ):
                proposals.append(
                    TagProposal(
                        dimension=TagDimension.FACHGEBIET,
                        label=label,
                        source=TagSource.FOLDER,
                    )
                )
        return proposals

    def propose_for_entry(self, entry: KnowledgeEntry) -> list[TagProposal]:
        if not entry.source_path:
            return []
        match = find_source_for_file(entry.source_path)
        if not match:
            return []
        source, source_root = match
        return self.propose(entry.source_path, source, source_root)



class ManualTagStrategy:
    """User-selected lookup IDs."""

    def propose(
        self,
        fachgebiet_ids: list[int] | None = None,
        diagnose_ids: list[int] | None = None,
        symptom_ids: list[int] | None = None,
    ) -> list[TagProposal]:
        proposals: list[TagProposal] = []
        for fid in fachgebiet_ids or []:
            proposals.append(
                TagProposal(
                    dimension=TagDimension.FACHGEBIET,
                    label="",
                    id=fid,
                    source=TagSource.MANUAL,
                )
            )
        for did in diagnose_ids or []:
            proposals.append(
                TagProposal(
                    dimension=TagDimension.DIAGNOSE,
                    label="",
                    id=did,
                    source=TagSource.MANUAL,
                )
            )
        for sid in symptom_ids or []:
            proposals.append(
                TagProposal(
                    dimension=TagDimension.SYMPTOM,
                    label="",
                    id=sid,
                    source=TagSource.MANUAL,
                )
            )
        return proposals


@dataclass
class TaggingService:
    db: Session
    folder: FolderHierarchyStrategy = field(default_factory=FolderHierarchyStrategy)
    manual: ManualTagStrategy = field(default_factory=ManualTagStrategy)

    def _set_lookup_source(self, obj, source: TagSource) -> None:
        if hasattr(obj, "source"):
            obj.source = source.value
        if hasattr(obj, "needs_review") and source != TagSource.SEED:
            pass  # set by resolver

    def _resolve_proposal(self, proposal: TagProposal) -> ResolutionResult | None:
        if proposal.dimension == TagDimension.FACHGEBIET:
            if proposal.id:
                return ResolutionResult(id=proposal.id, needs_review=False, is_new=False)
            if not proposal.label:
                return None
            result = resolve_fachgebiet(self.db, proposal.label, fuzzy=True)
            self._update_lookup_meta(Fachgebiet, result, proposal.source)
            return result
        if proposal.dimension == TagDimension.DIAGNOSE:
            if proposal.id:
                return ResolutionResult(id=proposal.id, needs_review=False, is_new=False)
            if not proposal.label and not proposal.code:
                return None
            result = resolve_diagnose(self.db, code=proposal.code, name=proposal.label or None)
            self._update_lookup_meta(Diagnose, result, proposal.source)
            return result
        if proposal.dimension == TagDimension.SYMPTOM:
            if proposal.id:
                return ResolutionResult(id=proposal.id, needs_review=False, is_new=False)
            if not proposal.label:
                return None
            result = resolve_symptom(self.db, proposal.label)
            self._update_lookup_meta(Symptom, result, proposal.source)
            return result
        return None

    def _update_lookup_meta(
        self, model, result: ResolutionResult, source: TagSource
    ) -> None:
        if not result.is_new:
            return
        obj = self.db.query(model).filter(model.id == result.id).first()
        if obj is None:
            return
        if hasattr(obj, "source"):
            obj.source = source.value
        if hasattr(obj, "needs_review"):
            obj.needs_review = result.needs_review
        if hasattr(obj, "beschreibung") and result.needs_review:
            obj.beschreibung = "[AUTO-CREATED] Pending admin review"

    def apply_proposals(
        self,
        entry: KnowledgeEntry,
        proposals: list[TagProposal],
        *,
        merge: bool = True,
    ) -> ApplyResult:
        result = ApplyResult()
        stored_hierarchy: list[str] = list(entry.source_hierarchy or []) if merge else []

        for proposal in proposals:
            if proposal.dimension == TagDimension.DOKUMENTTYP:
                if proposal.label:
                    typ_result = resolve_dokumenttyp(
                        self.db, proposal.label, source=proposal.source.value
                    )
                    entry.dokumenttyp_id = typ_result.id
                    entry.dokumenttyp = proposal.label  # dual-write legacy string
                    if typ_result.needs_review:
                        result.needs_review_count += 1
                    result.dokumenttyp_set = True
                continue

            if proposal.dimension == TagDimension.HIERARCHY:
                if proposal.label and proposal.label.lower() not in {
                    h.lower() for h in stored_hierarchy
                }:
                    stored_hierarchy.append(proposal.label)
                    result.hierarchy_added += 1
                    # Unified dual-write: link the OrdnerLabel row as well.
                    # Case-insensitive: resolve_ordner_label matches that way,
                    # and a case-variant duplicate INSERT violates the PK.
                    if proposal.label.lower() not in {
                        o.name.lower() for o in entry.ordner_labels
                    }:
                        label_result = resolve_ordner_label(
                            self.db, proposal.label, source=proposal.source.value
                        )
                        label_row = (
                            self.db.query(OrdnerLabel)
                            .filter(OrdnerLabel.id == label_result.id)
                            .first()
                        )
                        if label_row:
                            entry.ordner_labels.append(label_row)
                        if label_result.needs_review:
                            result.needs_review_count += 1
                continue

            resolved = self._resolve_proposal(proposal)
            if resolved is None:
                continue
            if resolved.needs_review:
                result.needs_review_count += 1

            if proposal.dimension == TagDimension.FACHGEBIET:
                existing = {f.id for f in entry.fachgebiete}
                if resolved.id not in existing:
                    fach = self.db.query(Fachgebiet).filter(Fachgebiet.id == resolved.id).first()
                    if fach:
                        entry.fachgebiete.append(fach)
                        result.fachgebiete_added += 1
            elif proposal.dimension == TagDimension.DIAGNOSE:
                existing = {d.id for d in entry.diagnosen}
                if resolved.id not in existing:
                    diag = self.db.query(Diagnose).filter(Diagnose.id == resolved.id).first()
                    if diag:
                        entry.diagnosen.append(diag)
                        result.diagnosen_added += 1
            elif proposal.dimension == TagDimension.SYMPTOM:
                existing = {s.id for s in entry.symptome}
                if resolved.id not in existing:
                    sym = self.db.query(Symptom).filter(Symptom.id == resolved.id).first()
                    if sym:
                        entry.symptome.append(sym)
                        result.symptome_added += 1

        entry.source_hierarchy = stored_hierarchy
        if stored_hierarchy:
            entry.unterkategorie = stored_hierarchy[-1]
        return result

    def apply_folder_hierarchy(
        self,
        entry: KnowledgeEntry,
        file_path: Path | str,
        source: SourceConfig,
        source_root: Path,
        *,
        merge: bool = True,
    ) -> ApplyResult:
        proposals = self.folder.propose(file_path, source, source_root)
        return self.apply_proposals(entry, proposals, merge=merge)

    def apply_folder_for_entry(
        self,
        entry: KnowledgeEntry,
        *,
        merge: bool = True,
    ) -> ApplyResult:
        if not entry.source_path:
            return ApplyResult()
        match = find_source_for_file(entry.source_path)
        if not match:
            return ApplyResult()
        source, source_root = match
        return self.apply_folder_hierarchy(
            entry, entry.source_path, source, source_root, merge=merge
        )

    def resolve_labels_to_ids(
        self,
        fachgebiete: list[str] | None = None,
        diagnosen: list | None = None,
        symptome: list[str] | None = None,
        *,
        dokumenttyp: str | None = None,
        ordner_labels: list[str] | None = None,
        source: TagSource = TagSource.LLM,
    ) -> dict:
        """Resolve string labels to lookup IDs (creates missing rows). For UI apply flows."""
        resolved = resolve_classifications(
            self.db,
            fachgebiet=(fachgebiete or [""])[0] if fachgebiete else "",
            diagnosen=diagnosen or [],
            symptome=symptome or [],
        )
        for model, key in [
            (Fachgebiet, "fachgebiet"),
        ]:
            item = resolved.get(key)
            if item and item.is_new:
                self._update_lookup_meta(model, item, source)

        for item in resolved.get("diagnosen", []):
            if item.is_new:
                self._update_lookup_meta(Diagnose, item, source)
        for item in resolved.get("symptome", []):
            if item.is_new:
                self._update_lookup_meta(Symptom, item, source)

        needs_review_count = resolved.get("needs_review_count", 0)

        dokumenttyp_id: int | None = None
        if dokumenttyp and dokumenttyp.strip():
            typ_result = resolve_dokumenttyp(
                self.db, dokumenttyp, source=source.value
            )
            dokumenttyp_id = typ_result.id
            if typ_result.needs_review:
                needs_review_count += 1

        resolved_ordner_ids: list[int] = []
        for label in ordner_labels or []:
            if not label.strip():
                continue
            label_result = resolve_ordner_label(self.db, label, source=source.value)
            resolved_ordner_ids.append(label_result.id)
            if label_result.needs_review:
                needs_review_count += 1

        self.db.commit()
        return {
            "fachgebiet_ids": [resolved["fachgebiet"].id] if resolved.get("fachgebiet") else [],
            "diagnose_ids": [d.id for d in resolved.get("diagnosen", [])],
            "symptom_ids": [s.id for s in resolved.get("symptome", [])],
            "dokumenttyp_id": dokumenttyp_id,
            "ordner_label_ids": resolved_ordner_ids,
            "needs_review_count": needs_review_count,
        }

    def get_suggestions(self, entry: KnowledgeEntry) -> dict:
        """Compare folder-derived labels with stored state."""
        path_proposals = self.folder.propose_for_entry(entry)
        path_hierarchy = [
            p.label
            for p in path_proposals
            if p.dimension == TagDimension.HIERARCHY and p.label
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        path_hierarchy_deduped: list[str] = []
        for label in path_hierarchy:
            if label not in seen:
                seen.add(label)
                path_hierarchy_deduped.append(label)

        stored = list(entry.source_hierarchy or [])
        stored_set = set(stored)
        missing_hierarchy = [label for label in path_hierarchy_deduped if label not in stored_set]

        dokumenttyp_proposal = next(
            (p for p in path_proposals if p.dimension == TagDimension.DOKUMENTTYP),
            None,
        )
        path_dokumenttyp = dokumenttyp_proposal.label if dokumenttyp_proposal else None

        curated_matches = []
        for label in path_hierarchy_deduped:
            fach = (
                self.db.query(Fachgebiet)
                .filter(Fachgebiet.name.ilike(label))
                .first()
            )
            existing_ids = {f.id for f in entry.fachgebiete}
            curated_matches.append(
                {
                    "label": label,
                    "id": fach.id if fach else None,
                    "already_linked": fach.id in existing_ids if fach else False,
                }
            )

        has_actionable = bool(missing_hierarchy) or (
            path_dokumenttyp and path_dokumenttyp != entry.dokumenttyp
        ) or any(
            m["id"] is not None and not m["already_linked"] for m in curated_matches
        )

        return {
            "source_path": entry.source_path,
            "unterkategorie": path_hierarchy_deduped[-1] if path_hierarchy_deduped else None,
            "dokumenttyp": path_dokumenttyp,
            "stored_dokumenttyp": entry.dokumenttyp,
            "hierarchy_labels": path_hierarchy_deduped,
            "stored_hierarchy": stored,
            "missing_hierarchy": missing_hierarchy,
            "fachgebiete": curated_matches,
            "has_actionable_suggestions": has_actionable,
        }
