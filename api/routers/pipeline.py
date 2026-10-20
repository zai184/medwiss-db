"""Pipeline endpoint for document processing.

Provides POST /process-file endpoint that accepts file uploads and
extracts text via the pipeline orchestrator (OCR/direct read).
"""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from api.config import settings
from api.models import PipelineResult
from pipeline.ocr_backend import NoOcrBackendError, http_error_for_ocr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/process-file", response_model=PipelineResult)
async def process_uploaded_file(
    file: UploadFile = File(..., description="Medical document to process"),
):
    """Process an uploaded medical document.

    Accepts a file upload, extracts text using OCR or direct reading,
    and returns the extracted text.

    Supported file types:
    - Images: PNG, JPG, JPEG, BMP, TIFF, PDF
    - Audio: MP3, WAV, M4A, OGG, FLAC
    - Text: TXT, MD, CSV, JSON, XML, YAML

    Args:
        file: Uploaded file to process

    Returns:
        PipelineResult with extracted text and metadata

    Raises:
        413: File size exceeds maximum allowed size
        422: Invalid file type or processing error
        500: Internal server error during processing
    """
    temp_dir = None
    temp_file_path = None

    try:
        if file.size is not None and file.size > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({settings.max_file_size_mb}MB)",
            )

        # Create temp directory and save file
        temp_dir = tempfile.mkdtemp(prefix="medwiss_pipeline_")

        # Generate unique filename preserving original extension
        original_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4().hex}{original_extension}"
        temp_file_path = Path(temp_dir) / unique_filename

        # Save uploaded file to temp location
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Saved uploaded file to: {temp_file_path}")

        # Process file through pipeline orchestrator (extraction only)
        from pipeline.orchestrator import detect_file_type, extract_text
        import time

        start_time = time.time()

        # Detect file type
        file_type = detect_file_type(temp_file_path)
        if file_type == "unknown":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported file type: {original_extension}",
            )

        # Extract text
        try:
            extracted_text = extract_text(temp_file_path, file_type)
        except NoOcrBackendError as e:
            status_code, detail = http_error_for_ocr(e)
            raise HTTPException(status_code=status_code, detail=detail)
        if not extracted_text or not extracted_text.strip():
            logger.warning(f"No text extracted from file: {file.filename}")
            extracted_text = ""

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Build response
        return PipelineResult(
            success=True,
            file_type=file_type,
            extracted_text=extracted_text,
            processing_time_ms=processing_time_ms,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Pipeline processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )
    finally:
        # Clean up temp file and directory
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file_path}: {e}")

        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
