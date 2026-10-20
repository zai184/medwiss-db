"""Deterministic regex-based classification of entries.

Reads a keyword library (data/classification_library.txt) and matches each
entry's folder path (Fachgebiet) and filename (Diagnose, Symptom) against it.
No LLM involvement — pure regex, instant, reproducible.

Library format (one rule per line, # = comment):
    F|<keyword>|<display_name>              (match against folder path)
    D|<keyword>|<display_name>|<icd10?>     (match against filename)
    S|<keyword>|<display_name>              (match against filename)

The keyword is matched case-insensitively as a substring in the target.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from database.models import Diagnose, Fachgebiet, KnowledgeEntry, Symptom

logger = logging.getLogger(__name__)

from api.services.icd11 import ICD11Client  # noqa: E402

# Reuse classification resolver for DB linking (creates rows + needs_review)
from pipeline.classification_resolver import resolve_classifications  # noqa: E402


@dataclass
class Rule:
    """A single classification rule from the library."""

    kind: str            # "F" | "D" | "S"
    keyword: str
    name: str
    icd10: Optional[str] = None
    compiled: "re.Pattern[str]" = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(re.escape(self.keyword), re.IGNORECASE)


@dataclass
class ClassifyResult:
    """Result of applying the regex classifier."""

    total_entries: int = 0
    fachgebiete_assigned: int = 0
    diagnosen_assigned: int = 0
    symptome_assigned: int = 0
    entries_touched: int = 0
    icd11_enriched: int = 0
    dry_run: bool = False


class RegexClassifier:
    """Classify entries by regex-matching folder path + filename against a library."""

    def __init__(
        self,
        db: Session,
        library_path: Path | str | None = None,
        icd11: Optional["ICD11Client"] = None,
    ):
        self.db = db
        self.icd11 = icd11
        path = Path(library_path) if library_path else (
            Path(__file__).resolve().parent.parent.parent / "data" / "classification_library.txt"
        )
        self.rules: dict[str, list[Rule]] = {"F": [], "D": [], "S": []}
        self._load(path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Classification library not found: {path}")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            kind, keyword, name = parts[0], parts[1], parts[2]
            if kind not in self.rules:
                continue
            icd10 = parts[3] if len(parts) > 3 and parts[3] else None
            self.rules[kind].append(Rule(kind, keyword, name, icd10))
        logger.info(
            f"Loaded classification library: {len(self.rules['F'])} Fachgebiete, "
            f"{len(self.rules['D'])} Diagnosen, {len(self.rules['S'])} Symptome"
        )

    def _match(self, text: str, kind: str) -> list[Rule]:
        """Return all rules of a kind whose keyword matches text."""
        return [r for r in self.rules[kind] if r.compiled.search(text)]

    def classify_entry(
        self, entry: KnowledgeEntry
    ) -> tuple[list[Rule], list[Rule], list[Rule]]:
        """Classify one entry. Returns (fachgebiete, diagnosen, symptome) matches."""
        path = entry.source_path or ""
        parts = path.split("/")
        filename = parts[-1] if parts else ""
        folder = "/".join(parts[:-1])

        fachgebiete = self._match(folder, "F")
        # Also check the filename for Fachgebiet (Leitlinien derive from filename)
        if not fachgebiete:
            fachgebiete = self._match(filename, "F")
        diagnosen = self._match(filename, "D")
        symptome = self._match(filename, "S")
        return fachgebiete, diagnosen, symptome

    async def classify_all(
        self,
        *,
        force: bool = False,
        dry_run: bool = True,
        limit: int | None = None,
    ) -> ClassifyResult:
        """Classify all eligible entries and apply matched tags."""
        query = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.source_path.isnot(None),
            KnowledgeEntry.source_path != "",
        )
        if not force:
            # Only entries missing ALL tag types (fach, diagnose, symptom)
            query = query.filter(
                ~KnowledgeEntry.fachgebiete.any()
                & ~KnowledgeEntry.diagnosen.any()
                & ~KnowledgeEntry.symptome.any()
            )
        raw_entries = query.all()
        if limit:
            raw_entries = raw_entries[:limit]
        if not raw_entries:
            return ClassifyResult(total_entries=0, dry_run=dry_run)

        result = ClassifyResult(total_entries=len(raw_entries), dry_run=dry_run)

        for entry in raw_entries:
            fachgebiete, diagnosen, symptome = self.classify_entry(entry)
            touched = False

            if fachgebiete and not dry_run:
                self._assign_fachgebiete(entry, fachgebiete)
                result.fachgebiete_assigned += 1
                touched = True
            elif fachgebiete:
                result.fachgebiete_assigned += 1

            if diagnosen and not dry_run:
                self._assign_diagnosen(entry, diagnosen)
                result.diagnosen_assigned += 1
                touched = True
            elif diagnosen:
                result.diagnosen_assigned += 1

            if symptome and not dry_run:
                self._assign_symptome(entry, symptome)
                result.symptome_assigned += 1
                touched = True
            elif symptome:
                result.symptome_assigned += 1

            if touched or (fachgebiete or diagnosen or symptome):
                result.entries_touched += 1

        # ICD-11 enrichment (optional post-processing step)
        if not dry_run and self.icd11 and self.icd11.is_configured:
            result.icd11_enriched = await self._enrich_icd11()

        if not dry_run:
            self.db.commit()
            logger.info(
                f"Regex classification complete: {result.fachgebiete_assigned} Fachgebiete, "
                f"{result.diagnosen_assigned} Diagnosen, {result.symptome_assigned} Symptome"
            )

        return result

    async def _enrich_icd11(self) -> int:
        """Look up ICD-11 codes for diagnoses that lack one. Returns count enriched."""
        assert self.icd11 is not None
        # Diagnoses without an ICD-11 code, ordered by name to dedupe lookups
        missing = (
            self.db.query(Diagnose)
            .filter(
                Diagnose.icd11_code.is_(None),
                Diagnose.code.isnot(None),
                Diagnose.code != "",
            )
            .order_by(Diagnose.name)
            .all()
        )
        count = 0
        seen_names: set[str] = set()
        for d in missing:
            if d.name in seen_names:
                continue
            seen_names.add(d.name)
            try:
                results = await self.icd11.search(d.name)
                if results:
                    d.icd11_code = results[0].code
                    count += 1
            except Exception as e:
                logger.warning(f"ICD-11 lookup failed for '{d.name}': {e}")
        return count

    def _assign_fachgebiete(self, entry: KnowledgeEntry, rules: list[Rule]) -> None:
        # Deduplicate by display name (multiple keywords may map to one specialty)
        seen_names: set[str] = set()
        unique_rules: list[Rule] = []
        for r in rules:
            if r.name not in seen_names:
                seen_names.add(r.name)
                unique_rules.append(r)
        fach_ids: list[int] = []
        for rule in unique_rules:
            resolved = resolve_classifications(
                self.db, fachgebiet=rule.name, diagnosen=[], symptome=[]
            )
            fach = resolved.get("fachgebiet")
            if fach and hasattr(fach, "id"):
                fach_ids.append(fach.id)
        if fach_ids:
            existing = {f.id for f in entry.fachgebiete}
            for fid in fach_ids:
                if fid not in existing:
                    f = self.db.get(Fachgebiet, fid)
                    if f:
                        entry.fachgebiete.append(f)

    def _assign_diagnosen(self, entry: KnowledgeEntry, rules: list[Rule]) -> None:
        diag_dicts = [{"code": r.icd10 or "", "name": r.name} for r in rules]
        resolved = resolve_classifications(
            self.db, fachgebiet="", diagnosen=diag_dicts, symptome=[]
        )
        diag_ids = [d.id for d in resolved.get("diagnosen", [])] if resolved.get("diagnosen") else []
        if diag_ids:
            existing = {d.id for d in entry.diagnosen}
            for did in diag_ids:
                if did not in existing:
                    d = self.db.get(Diagnose, did)
                    if d:
                        entry.diagnosen.append(d)

    def _assign_symptome(self, entry: KnowledgeEntry, rules: list[Rule]) -> None:
        sym_names = [r.name for r in rules]
        resolved = resolve_classifications(
            self.db, fachgebiet="", diagnosen=[], symptome=sym_names
        )
        sym_ids = [s.id for s in resolved.get("symptome", [])] if resolved.get("symptome") else []
        if sym_ids:
            existing = {s.id for s in entry.symptome}
            for sid in sym_ids:
                if sid not in existing:
                    s = self.db.get(Symptom, sid)
                    if s:
                        entry.symptome.append(s)
