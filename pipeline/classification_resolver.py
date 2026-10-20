"""Classification resolver for matching LLM output to database IDs.

This module provides fuzzy matching and resolution of classification data
from the LLM classifier to existing database records. New classifications
are created with a `needs_review` flag for admin approval.

Features:
- Fuzzy matching for slight variations (case-insensitive, whitespace normalization)
- In-memory caching for repeated lookups
- Admin approval queue via `needs_review` flag
- Proper database session handling
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import Diagnose, Dokumenttyp, Fachgebiet, OrdnerLabel, Symptom

logger = logging.getLogger(__name__)

# Simple in-memory cache for classification lookups
# Structure: {cache_key: (id, needs_review)}
_classification_cache: dict[str, tuple[int, bool]] = {}


@dataclass
class ResolutionResult:
    """Result of resolving a classification to a database ID.

    Attributes:
        id: Database ID of the classification
        needs_review: True if this is a new classification awaiting admin approval
        is_new: True if this classification was just created
    """

    id: int
    needs_review: bool
    is_new: bool


def _normalize_name(name: str) -> str:
    """Normalize a classification name for fuzzy matching.

    Normalization steps:
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Collapse multiple spaces to single space
    4. Remove common punctuation variations

    Args:
        name: Raw classification name from LLM output

    Returns:
        Normalized name suitable for comparison
    """
    if not name:
        return ""

    # Strip whitespace and lowercase
    normalized = name.strip().lower()

    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)

    # Remove common punctuation that might vary
    normalized = re.sub(r"[.,;:!?]$", "", normalized)

    return normalized


def _get_cache_key(entity_type: str, identifier: str) -> str:
    """Generate a cache key for the classification cache.

    Args:
        entity_type: Type of entity ('fachgebiet', 'diagnose', 'symptom')
        identifier: Normalized name or code

    Returns:
        Cache key string
    """
    return f"{entity_type}:{_normalize_name(identifier)}"


def _find_fuzzy_fachgebiet(db: Session, name: str) -> Optional[Fachgebiet]:
    """Find a Fachgebiet using fuzzy matching.

    Tries exact match first, then case-insensitive, then pg_trgm similarity.

    Args:
        db: Database session
        name: Fachgebiet name to search for

    Returns:
        Matching Fachgebiet or None
    """
    normalized = _normalize_name(name)
    if not normalized:
        return None

    # Try exact match first (case-insensitive)
    result = db.query(Fachgebiet).filter(func.lower(Fachgebiet.name) == normalized).first()
    if result:
        return result

    # Try pg_trgm similarity for fuzzy matching
    # similarity > 0.6 is a reasonable threshold for "close enough"
    result = (
        db.query(Fachgebiet)
        .filter(func.similarity(func.lower(Fachgebiet.name), normalized) > 0.6)
        .order_by(func.similarity(func.lower(Fachgebiet.name), normalized).desc())
        .first()
    )

    return result


def _find_fuzzy_diagnose(
    db: Session, code: Optional[str] = None, name: Optional[str] = None
) -> Optional[Diagnose]:
    """Find a Diagnose using fuzzy matching.

    Tries code match first (if provided), then name matching.

    Args:
        db: Database session
        code: ICD-10 code (optional)
        name: Diagnose name to search for (optional)

    Returns:
        Matching Diagnose or None
    """
    # Try code match first if provided
    if code:
        code_normalized = code.strip().upper()
        result = db.query(Diagnose).filter(func.upper(Diagnose.code) == code_normalized).first()
        if result:
            return result

    # Try name match if provided
    if name:
        normalized = _normalize_name(name)
        if normalized:
            # Exact match (case-insensitive)
            result = db.query(Diagnose).filter(func.lower(Diagnose.name) == normalized).first()
            if result:
                return result

            # Fuzzy match with pg_trgm
            result = (
                db.query(Diagnose)
                .filter(func.similarity(func.lower(Diagnose.name), normalized) > 0.6)
                .order_by(func.similarity(func.lower(Diagnose.name), normalized).desc())
                .first()
            )
            if result:
                return result

    return None


def _find_fuzzy_symptom(db: Session, name: str) -> Optional[Symptom]:
    """Find a Symptom using fuzzy matching.

    Tries exact match first, then case-insensitive, then pg_trgm similarity.

    Args:
        db: Database session
        name: Symptom name to search for

    Returns:
        Matching Symptom or None
    """
    normalized = _normalize_name(name)
    if not normalized:
        return None

    # Try exact match (case-insensitive)
    result = db.query(Symptom).filter(func.lower(Symptom.name) == normalized).first()
    if result:
        return result

    # Try pg_trgm similarity
    result = (
        db.query(Symptom)
        .filter(func.similarity(func.lower(Symptom.name), normalized) > 0.6)
        .order_by(func.similarity(func.lower(Symptom.name), normalized).desc())
        .first()
    )

    return result


def resolve_fachgebiet(db: Session, name: str, *, fuzzy: bool = True) -> ResolutionResult:
    """Resolve a Fachgebiet name to a database ID.

    Looks up existing Fachgebiet using fuzzy matching (by default). If not found,
    creates a new Fachgebiet with needs_review=True.

    Args:
        db: Database session
        name: Fachgebiet name from LLM classification

    Returns:
        ResolutionResult with ID and review status

    Example:
        >>> result = resolve_fachgebiet(db, "Kardiologie")
        >>> print(f"ID: {result.id}, Needs review: {result.needs_review}")
    """
    if not name or not name.strip():
        raise ValueError("Fachgebiet name cannot be empty")

    # Check cache first
    cache_key = _get_cache_key("fachgebiet", name)
    if cache_key in _classification_cache:
        cached_id, cached_needs_review = _classification_cache[cache_key]
        logger.debug(f"Cache hit for fachgebiet '{name}' -> ID {cached_id}")
        return ResolutionResult(id=cached_id, needs_review=cached_needs_review, is_new=False)

    # Try to find existing
    if fuzzy:
        existing = _find_fuzzy_fachgebiet(db, name)
    else:
        normalized = _normalize_name(name)
        existing = (
            db.query(Fachgebiet).filter(func.lower(Fachgebiet.name) == normalized).first()
            if normalized
            else None
        )
    if existing:
        logger.debug(f"Found existing fachgebiet '{name}' -> ID {existing.id}")
        _classification_cache[cache_key] = (existing.id, False)
        return ResolutionResult(id=existing.id, needs_review=False, is_new=False)

    # Create new with needs_review flag
    # Note: needs_review field must be added to Fachgebiet model
    # For now, we store it in beschreibung as a workaround
    new_fach = Fachgebiet(
        name=name.strip(),
        beschreibung="[AUTO-CREATED] Pending admin review",
        needs_review=True,
        source="llm",
    )
    db.add(new_fach)
    db.flush()  # Get the ID without committing

    logger.info(f"Created new fachgebiet '{name}' with ID {new_fach.id} (needs review)")
    _classification_cache[cache_key] = (new_fach.id, True)

    return ResolutionResult(id=new_fach.id, needs_review=True, is_new=True)


def resolve_diagnose(
    db: Session, code: Optional[str] = None, name: Optional[str] = None
) -> ResolutionResult:
    """Resolve a Diagnose code/name to a database ID.

    Looks up existing Diagnose using code (if provided) or fuzzy name matching.
    If not found, creates a new Diagnose with needs_review=True.

    Args:
        db: Database session
        code: ICD-10 code (optional but preferred)
        name: Diagnose name (optional, used if code not provided)

    Returns:
        ResolutionResult with ID and review status

    Raises:
        ValueError: If both code and name are empty/None

    Example:
        >>> result = resolve_diagnose(db, code="J18.9", name="Pneumonie")
        >>> print(f"ID: {result.id}, Needs review: {result.needs_review}")
    """
    if not code and not name:
        raise ValueError("Either code or name must be provided for diagnose resolution")

    # Build cache key (code preferred, fallback to name)
    cache_identifier = code if code else name
    assert cache_identifier is not None  # Validated above
    cache_key = _get_cache_key("diagnose", cache_identifier)

    if cache_key in _classification_cache:
        cached_id, cached_needs_review = _classification_cache[cache_key]
        logger.debug(f"Cache hit for diagnose '{cache_identifier}' -> ID {cached_id}")
        return ResolutionResult(id=cached_id, needs_review=cached_needs_review, is_new=False)

    # Try to find existing
    existing = _find_fuzzy_diagnose(db, code=code, name=name)
    if existing:
        logger.debug(f"Found existing diagnose '{code or name}' -> ID {existing.id}")
        _classification_cache[cache_key] = (existing.id, False)
        return ResolutionResult(id=existing.id, needs_review=False, is_new=False)

    # Create new with needs_review flag
    # Note: needs_review field must be added to Diagnose model
    # For now, we indicate auto-creation in beschreibung
    code_clean = code.strip().upper() if code else ""
    name_clean = name.strip() if name else ""

    if not name_clean and code_clean:
        # If only code provided, use code as name temporarily
        name_clean = f"[Unbekannt: {code_clean}]"

    new_diagnose = Diagnose(
        code=code_clean if code_clean else f"TEMP-{name_clean[:20]}",
        name=name_clean,
        beschreibung="[AUTO-CREATED] Pending admin review",
        needs_review=True,
        source="llm",
    )
    db.add(new_diagnose)
    db.flush()

    logger.info(f"Created new diagnose '{code or name}' with ID {new_diagnose.id} (needs review)")
    _classification_cache[cache_key] = (new_diagnose.id, True)

    return ResolutionResult(id=new_diagnose.id, needs_review=True, is_new=True)


def resolve_symptom(db: Session, name: str) -> ResolutionResult:
    """Resolve a Symptom name to a database ID.

    Looks up existing Symptom using fuzzy matching. If not found,
    creates a new Symptom with needs_review=True.

    Args:
        db: Database session
        name: Symptom name from LLM classification

    Returns:
        ResolutionResult with ID and review status

    Example:
        >>> result = resolve_symptom(db, "Fieber")
        >>> print(f"ID: {result.id}, Needs review: {result.needs_review}")
    """
    if not name or not name.strip():
        raise ValueError("Symptom name cannot be empty")

    # Check cache first
    cache_key = _get_cache_key("symptom", name)
    if cache_key in _classification_cache:
        cached_id, cached_needs_review = _classification_cache[cache_key]
        logger.debug(f"Cache hit for symptom '{name}' -> ID {cached_id}")
        return ResolutionResult(id=cached_id, needs_review=cached_needs_review, is_new=False)

    # Try to find existing
    existing = _find_fuzzy_symptom(db, name)
    if existing:
        logger.debug(f"Found existing symptom '{name}' -> ID {existing.id}")
        _classification_cache[cache_key] = (existing.id, False)
        return ResolutionResult(id=existing.id, needs_review=False, is_new=False)

    # Create new with needs_review flag
    # Note: needs_review field must be added to Symptom model
    # For now, we store it in beschreibung as a workaround
    new_symptom = Symptom(
        name=name.strip(),
        beschreibung="[AUTO-CREATED] Pending admin review",
        needs_review=True,
        source="llm",
    )
    db.add(new_symptom)
    db.flush()

    logger.info(f"Created new symptom '{name}' with ID {new_symptom.id} (needs review)")
    _classification_cache[cache_key] = (new_symptom.id, True)

    return ResolutionResult(id=new_symptom.id, needs_review=True, is_new=True)


def _resolve_simple_lookup(
    db: Session, model, kind: str, name: str, source: str
) -> ResolutionResult:
    """Resolve a simple name-only lookup row (Dokumenttyp, OrdnerLabel).

    Exact case-insensitive match first; creates the row when missing.
    Folder-sourced rows are trusted (needs_review=False); LLM-sourced rows
    enter the admin review queue (needs_review=True).
    """
    if not name or not name.strip():
        raise ValueError(f"{kind} name cannot be empty")

    normalized = name.strip()
    cache_key = _get_cache_key(kind.lower(), normalized)
    if cache_key in _classification_cache:
        cached_id, cached_needs_review = _classification_cache[cache_key]
        return ResolutionResult(id=cached_id, needs_review=cached_needs_review, is_new=False)

    existing = db.query(model).filter(func.lower(model.name) == normalized.lower()).first()
    if existing:
        _classification_cache[cache_key] = (existing.id, False)
        return ResolutionResult(id=existing.id, needs_review=False, is_new=False)

    needs_review = source == "llm"
    new_row = model(
        name=normalized,
        needs_review=needs_review,
        source=source,
    )
    db.add(new_row)
    db.flush()

    logger.info(
        f"Created new {kind.lower()} '{normalized}' with ID {new_row.id}"
        + (" (needs review)" if needs_review else "")
    )
    _classification_cache[cache_key] = (new_row.id, needs_review)
    return ResolutionResult(id=new_row.id, needs_review=needs_review, is_new=True)


def resolve_dokumenttyp(db: Session, name: str, *, source: str = "llm") -> ResolutionResult:
    """Resolve a Dokumenttyp name to a database ID (creates the row when missing)."""
    return _resolve_simple_lookup(db, Dokumenttyp, "Dokumenttyp", name, source)


def resolve_ordner_label(db: Session, name: str, *, source: str = "llm") -> ResolutionResult:
    """Resolve an OrdnerLabel name to a database ID (creates the row when missing)."""
    return _resolve_simple_lookup(db, OrdnerLabel, "OrdnerLabel", name, source)


def clear_cache() -> None:
    """Clear the classification lookup cache.

    Useful for testing or when classifications have been modified
    by an admin and fresh lookups are needed.
    """
    global _classification_cache
    _classification_cache.clear()
    logger.debug("Classification cache cleared")


def get_cache_stats() -> dict:
    """Get statistics about the classification cache.

    Returns:
        Dict with cache size and entries
    """
    return {
        "size": len(_classification_cache),
        "entries": list(_classification_cache.keys()),
    }


def resolve_classifications(
    db: Session,
    fachgebiet: str,
    diagnosen: list[dict],
    symptome: list[str],
) -> dict:
    """Resolve all classifications from a ClassificationResult.

    Convenience function to resolve all classifications at once.

    Args:
        db: Database session
        fachgebiet: Fachgebiet name
        diagnosen: List of diagnose dicts with 'code' and 'name' keys
        symptome: List of symptom names

    Returns:
        Dict with resolved IDs:
        {
            'fachgebiet': ResolutionResult,
            'diagnosen': [ResolutionResult, ...],
            'symptome': [ResolutionResult, ...],
            'needs_review_count': int  # Total items needing review
        }
    """
    results = {
        "fachgebiet": None,
        "diagnosen": [],
        "symptome": [],
        "needs_review_count": 0,
    }

    # Resolve fachgebiet
    if fachgebiet:
        fach_result = resolve_fachgebiet(db, fachgebiet)
        results["fachgebiet"] = fach_result
        if fach_result.needs_review:
            results["needs_review_count"] += 1

    # Resolve diagnosen
    for diag in diagnosen:
        if isinstance(diag, dict):
            diag_result = resolve_diagnose(db, code=diag.get("code"), name=diag.get("name"))
        elif isinstance(diag, str):
            # Handle string-only diagnoses
            diag_result = resolve_diagnose(db, name=diag)
        else:
            continue

        results["diagnosen"].append(diag_result)
        if diag_result.needs_review:
            results["needs_review_count"] += 1

    # Resolve symptome
    for symptom_name in symptome:
        if symptom_name and symptom_name.strip():
            sym_result = resolve_symptom(db, symptom_name)
            results["symptome"].append(sym_result)
            if sym_result.needs_review:
                results["needs_review_count"] += 1

    return results
