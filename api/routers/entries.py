"""CRUD endpoints for Knowledge Entries.

Business logic is in api/services/entry_service.py.
This router handles HTTP concerns only: validation, auth, error responses.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import (
    EntryCreate,
    EntryListResponse,
    EntryResponse,
    EntryTagSuggestionsResponse,
    EntryUpdate,
)
from api.services.entry_service import EntryService

router = APIRouter(prefix="/entries", tags=["entries"])


def _get_service(db: Session) -> EntryService:
    return EntryService(db)


def _handle_value_error(e: ValueError) -> HTTPException:
    """Map ValueError from service to 404 HTTPException."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/dokumenttypen", response_model=list[str])
async def get_dokumenttypen(db: Session = Depends(get_db)):
    """Get all distinct dokumenttyp values from entries."""
    return _get_service(db).get_dokumenttypen()


@router.get("", response_model=EntryListResponse)
async def list_entries(
    limit: int = Query(20, ge=1, le=10000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    dokumenttyp: list[str] = Query(default=[], description="Filter by dokumenttyp (can be specified multiple times)"),
    schwierigkeit: Optional[str] = Query(None, description="Filter by schwierigkeit"),
    fach: Optional[list[str]] = Query(None, description="Filter by fachgebiet names"),
    diagnose: Optional[list[str]] = Query(None, description="Filter by diagnose names"),
    symptom: Optional[list[str]] = Query(None, description="Filter by symptom names"),
    source_path: Optional[str] = Query(None, description="Filter: entries whose source_path contains this substring (e.g. '2_Notfall/00_Notfall_SOPs')"),
    db: Session = Depends(get_db),
):
    """Get a paginated list of knowledge entries with optional filters."""
    return _get_service(db).list_entries(
        limit=limit,
        offset=offset,
        dokumenttypen=dokumenttyp or None,
        schwierigkeit=schwierigkeit,
        fach=fach,
        diagnose=diagnose,
        symptom=symptom,
        source_path=source_path,
    )


@router.get("/{entry_id}/tag-suggestions", response_model=EntryTagSuggestionsResponse)
async def get_entry_tag_suggestions(entry_id: int, db: Session = Depends(get_db)):
    """Get folder-path Fachgebiet suggestions for an entry."""
    try:
        return _get_service(db).get_tag_suggestions(entry_id)
    except ValueError as e:
        raise _handle_value_error(e)


@router.post(
    "/{entry_id}/tag-suggestions/apply",
    response_model=EntryTagSuggestionsResponse,
)
async def apply_entry_tag_suggestions(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Apply missing folder hierarchy labels to entry metadata."""
    try:
        return _get_service(db).apply_tag_suggestions(entry_id)
    except ValueError as e:
        raise _handle_value_error(e)



@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: int, db: Session = Depends(get_db)):
    """Get a single knowledge entry by ID."""
    try:
        return _get_service(db).get_entry(entry_id)
    except ValueError as e:
        raise _handle_value_error(e)


@router.post("", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: EntryCreate,
    db: Session = Depends(get_db),
):
    """Create a new knowledge entry."""
    return _get_service(db).create_entry(entry_data, None)


@router.put("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: int,
    entry_data: EntryUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing knowledge entry."""
    try:
        return _get_service(db).update_entry(entry_id, entry_data, None)
    except ValueError as e:
        raise _handle_value_error(e)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Delete a knowledge entry."""
    try:
        _get_service(db).delete_entry(entry_id)
    except ValueError as e:
        raise _handle_value_error(e)
    return None