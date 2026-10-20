"""Summarization endpoint for knowledge entries.

Provides POST /entries/{entry_id}/summarize endpoint that extracts text
from an entry's linked file and generates a summary using the configured
AI provider and skill.
"""
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from api.database import get_db
from api.models import (
    SummarizeRequest,
    SummarizeResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from database.models import KnowledgeEntry
from pipeline.ocr_backend import NoOcrBackendError, http_error_for_ocr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entries", tags=["entries"])

VALID_SKILLS = {"studie", "leitlinie", "screenshot", "standard"}


@router.post("/{entry_id}/transcribe", response_model=TranscribeResponse)
async def transcribe_entry(
    entry_id: int,
    request: TranscribeRequest = TranscribeRequest(),
    db: Session = Depends(get_db),
):
    """Transcribe (OCR-extract) a knowledge entry's linked file — no LLM.

    Runs the on-demand OCR seam for image/PDF, or a direct read for text
    files. Returns only the extracted raw text; no summarization.

    Raises:
        404: Entry not found
        400: Entry has no linked file
        409/502: No OCR backend available / backends failed (image/PDF)
    """
    entry = (
        db.query(KnowledgeEntry)
        .options(
            joinedload(KnowledgeEntry.fachgebiete),
            joinedload(KnowledgeEntry.diagnosen),
            joinedload(KnowledgeEntry.symptome),
        )
        .filter(KnowledgeEntry.id == entry_id)
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry with ID {entry_id} not found",
        )

    if not entry.source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry {entry_id} has no linked file",
        )

    try:
        result = await asyncio.to_thread(
            _transcribe_file,
            file_path=entry.source_path,
            backend=request.backend,
        )
        return result

    except NoOcrBackendError as e:
        logger.info(f"OCR unavailable for entry {entry_id}: {e}")
        status_code, detail = http_error_for_ocr(e)
        raise HTTPException(status_code=status_code, detail=detail)
    except FileNotFoundError as e:
        logger.error(f"Linked file not found for entry {entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Linked file not found: {entry.source_path}",
        )
    except ValueError as e:
        logger.error(f"Invalid value for entry {entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Transcription failed for entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


def _transcribe_file(file_path: str, backend: str | None = None) -> TranscribeResponse:
    """Extract text from a file without any LLM summarization step."""
    from pathlib import Path

    from pipeline import orchestrator

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    file_type = orchestrator.detect_file_type(path)
    if file_type == "unknown":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    extracted_text = orchestrator.extract_text(path, file_type, backend=backend)
    return TranscribeResponse(
        success=True,
        extracted_text=extracted_text,
        file_type=file_type,
    )


@router.post("/{entry_id}/summarize", response_model=SummarizeResponse)
async def summarize_entry(
    entry_id: int,
    request: SummarizeRequest,
    db: Session = Depends(get_db),
):
    """Summarize a knowledge entry's linked file.

    Extracts text from the entry's linked file (OCR for image/PDF, direct
    read for text), then generates a summary using the specified AI
    provider and skill.

    Args:
        entry_id: ID of the knowledge entry to summarize
        request: Summarization request with skill, provider, and optional model

    Returns:
        SummarizeResponse with extracted text, summary, and metadata

    Raises:
        404: Entry not found
        400: Entry has no linked file or invalid skill
        422: Validation error
        500: Processing error
    """
    if request.skill not in VALID_SKILLS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid skill: {request.skill}. Must be one of: {', '.join(sorted(VALID_SKILLS))}",
        )

    entry = (
        db.query(KnowledgeEntry)
        .options(
            joinedload(KnowledgeEntry.fachgebiete),
            joinedload(KnowledgeEntry.diagnosen),
            joinedload(KnowledgeEntry.symptome),
        )
        .filter(KnowledgeEntry.id == entry_id)
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry with ID {entry_id} not found",
        )

    if not entry.source_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry {entry_id} has no linked file",
        )

    from pipeline import orchestrator

    if not hasattr(orchestrator, "summarize_file"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Summarization not yet implemented in pipeline orchestrator",
        )
    try:
        result = await asyncio.to_thread(
            orchestrator.summarize_file,
            file_path=entry.source_path,
            skill=request.skill,
            provider=request.provider,
            model=request.model,
        )

        return SummarizeResponse(
            success=result.get("success", True),
            extracted_text=result.get("extracted_text", ""),
            summary=result.get("summary", ""),
            model_used=result.get("model_used"),
            skill_used=request.skill,
        )

    except NoOcrBackendError as e:
        logger.info(f"OCR unavailable for entry {entry_id}: {e}")
        status_code, detail = http_error_for_ocr(e)
        raise HTTPException(status_code=status_code, detail=detail)
    except FileNotFoundError as e:
        logger.error(f"Linked file not found for entry {entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Linked file not found: {entry.source_path}",
        )
    except ValueError as e:
        logger.error(f"Invalid value for entry {entry_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Summarization failed for entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {str(e)}",
        )
