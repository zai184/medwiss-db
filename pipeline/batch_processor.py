"""Single-file processor for the medical file pipeline.

Provides single-file text extraction (OCR for images/PDF, direct read for
text) used by the file-sync ingest path. Batch/parallel directory processing
was removed 2026-09-07 per decision: OCR/extraction is on-demand only, never
batch. No scan_directory/process_directory remains.
"""

import hashlib
import logging
from pathlib import Path
from typing import Callable, Optional, Union

from pipeline.ocr import OCRDisabledError
from pipeline.orchestrator import (
    ProcessingResult,
    detect_file_type,
    extract_text,
)

logger = logging.getLogger(__name__)

BATCH_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".md", ".txt"}

ProgressCallback = Callable[[str, str, float], None]


class BatchProcessor:
    """Process a single file through the extraction pipeline.

    Provides progress reporting and per-file error handling without
    crashing on individual failures.

    Example:
        >>> processor = BatchProcessor()
        >>> result = processor.process_file("/path/to/document.pdf")
    """

    def __init__(
        self,
        supported_extensions: Optional[set[str]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        """Initialize the processor.

        Args:
            supported_extensions: File extensions to process (default: BATCH_EXTENSIONS)
            progress_callback: Optional callback for progress reporting
        """
        self.supported_extensions = supported_extensions or BATCH_EXTENSIONS
        self.progress_callback = progress_callback

    def _report_progress(self, file_path: str, status: str, progress: float) -> None:
        """Report progress through callback if configured.

        Args:
            file_path: Path to the file being processed
            status: Status (e.g., "extracting", "complete")
            progress: Progress percentage (0.0 to 100.0)
        """
        if self.progress_callback:
            try:
                self.progress_callback(str(file_path), status, progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def process_file(
        self,
        file_path: Union[str, Path],
    ) -> ProcessingResult:
        """Process a single file through the pipeline.

        This method:
        1. Validates the file exists and has a supported extension
        2. Detects file type
        3. Extracts text (OCR for images/PDF, direct read for text)
        4. Returns structured result

        Args:
            file_path: Path to the file to process

        Returns:
            ProcessingResult with extracted text
        """
        import time

        file_path = Path(file_path)
        start_time = time.time()

        self._report_progress(str(file_path), "starting", 0.0)

        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return ProcessingResult(
                file_path=str(file_path),
                file_type="unknown",
                extracted_text="",
                error=error_msg,
            )

        suffix = file_path.suffix.lower()
        if suffix not in self.supported_extensions:
            error_msg = f"Unsupported file extension: {suffix}"
            logger.warning(error_msg)
            return ProcessingResult(
                file_path=str(file_path),
                file_type="unknown",
                extracted_text="",
                error=error_msg,
            )

        try:
            file_type: str = "unknown"
            self._report_progress(str(file_path), "detecting_type", 10.0)
            file_type = detect_file_type(file_path)
            logger.info(f"Detected file type: {file_type} for {file_path}")

            if file_type == "unknown":
                error_msg = f"Unknown file type: {file_path.suffix}"
                logger.error(error_msg)
                return ProcessingResult(
                    file_path=str(file_path),
                    file_type="unknown",
                    extracted_text="",
                    error=error_msg,
                    processing_time_ms=(time.time() - start_time) * 1000,
                )

            self._report_progress(str(file_path), "extracting", 30.0)
            extracted_text = extract_text(file_path, file_type)
            processing_time = (time.time() - start_time) * 1000

            self._report_progress(str(file_path), "complete", 100.0)

            result = ProcessingResult(
                file_path=str(file_path),
                file_type=file_type,
                extracted_text=extracted_text,
                processing_time_ms=processing_time,
            )

            logger.info(f"Processing complete for {file_path} in {processing_time:.2f}ms")
            return result

        except OCRDisabledError:
            # OCR unavailable on this host: skip without error noise.
            # file_sync turns this into a link-only index for the file.
            logger.info(f"OCR unavailable, skipping text extraction for {file_path}")
            return ProcessingResult(
                file_path=str(file_path),
                file_type=file_type,
                extracted_text="",
                error=f"OCR unavailable (skipped): {file_path}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Processing failed for {file_path}: {e}", exc_info=True)
            processing_time = (time.time() - start_time) * 1000

            return ProcessingResult(
                file_path=str(file_path),
                file_type=detect_file_type(file_path) if file_path.exists() else "unknown",
                extracted_text="",
                error=str(e),
                processing_time_ms=processing_time,
            )


def calculate_file_hash(file_path: Union[str, Path]) -> str:
    """Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash as hexadecimal string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
