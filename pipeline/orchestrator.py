"""Pipeline orchestrator for processing medical files.

This module coordinates the processing of various file types through
appropriate extraction modules (text extraction, summarization).

Supported file types:
- Images (PNG, JPG, JPEG, BMP, TIFF) → OCR
- PDF documents → OCR
- Text files (TXT, MD) → Direct text extraction

Audio transcription (whisper) was removed 2026-09-07 — not needed. Audio
files stay link-only playable entries in the library.
"""

import json
import logging
import mimetypes
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import httpx

from api.config import settings
from pipeline.ocr_backend import NoOcrBackendError


logger = logging.getLogger(__name__)

SUMMARIZE_SKILLS = {"studie", "leitlinie", "screenshot", "standard"}

# File type mappings
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".aac"}
TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".json", ".xml", ".yaml", ".yml"}


@dataclass
class ProcessingResult:
    """Result of processing a file through the pipeline."""

    file_path: str
    file_type: str
    extracted_text: str
    processed_at: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None

    def __post_init__(self):
        if self.processed_at is None:
            self.processed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def detect_file_type(file_path: Union[str, Path]) -> str:
    """Detect the type of file based on extension.

    Args:
        file_path: Path to the file

    Returns:
        File type category: 'image', 'audio', 'text', or 'unknown'
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return "image"
    elif suffix in AUDIO_EXTENSIONS:
        return "audio"
    elif suffix in TEXT_EXTENSIONS:
        return "text"
    else:
        # Try MIME type detection as fallback
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            if mime_type.startswith("image/"):
                return "image"
            elif mime_type.startswith("audio/"):
                return "audio"
            elif mime_type.startswith("text/"):
                return "text"

        return "unknown"


def extract_text(file_path: Path, file_type: str, backend: str | None = None) -> str:
    """Extract text from file based on type.

    Args:
        file_path: Path to the file
        file_type: Detected file type
        backend: Optional OCR backend override (tesseract, openrouter-vision).
            None = run the configured OCR_BACKENDS seam in order.

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type is not supported
        RuntimeError: If extraction fails
    """
    if file_type == "image":
        # OCR is on-demand only: route through the ordered backend seam
        # (tesseract local / openrouter-vision via OPENROUTER_API_KEY).
        # No batch/ingest use.
        from pipeline.ocr_backend import extract_text_from_file

        logger.info(
            f"Extracting text from image via OCR seam ({backend or 'auto'}): {file_path}"
        )
        return extract_text_from_file(file_path, backend=backend)

    elif file_type == "audio":
        # Audio transcription (whisper) removed 2026-09-07. Audio files stay
        # in the library as playable link-only entries; no text extraction.
        raise ValueError(
            f"Audio transcription is not supported ({file_path}) — whisper removed"
        )

    elif file_type == "text":
        logger.info(f"Reading text file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _load_summarize_prompt(skill: str) -> str:
    if skill not in SUMMARIZE_SKILLS:
        raise ValueError(f"Invalid skill: {skill}. Must be one of: {', '.join(SUMMARIZE_SKILLS)}")

    prompt_path = Path(__file__).parent / "prompts" / "summarize" / f"{skill}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def summarize_file(
    file_path: Union[str, Path],
    skill: str,
    provider: str = "llamaserver",
    model: Optional[str] = None,
) -> dict:
    """Summarize a file using a specific skill prompt."""
    import time


    file_path = Path(file_path)
    start_time = time.time()

    logger.info(f"Starting summarization: {file_path} with skill={skill}, provider={provider}")

    if not file_path.exists():
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        return {
            "success": False,
            "extracted_text": "",
            "summary": "",
            "model_used": model or provider,
            "skill_used": skill,
            "error": error_msg,
        }

    if skill not in SUMMARIZE_SKILLS:
        error_msg = f"Invalid skill: {skill}. Must be one of: {', '.join(SUMMARIZE_SKILLS)}"
        logger.error(error_msg)
        return {
            "success": False,
            "extracted_text": "",
            "summary": "",
            "model_used": model or provider,
            "skill_used": skill,
            "error": error_msg,
        }

    try:
        file_type = detect_file_type(file_path)
        logger.info(f"Detected file type: {file_type}")

        if file_type == "unknown":
            error_msg = f"Unknown file type: {file_path.suffix}"
            logger.error(error_msg)
            return {
                "success": False,
                "extracted_text": "",
                "summary": "",
                "model_used": model or provider,
                "skill_used": skill,
                "error": error_msg,
            }

        extracted_text = extract_text(file_path, file_type)
        logger.info(f"Extracted {len(extracted_text)} characters")

        if not extracted_text.strip():
            error_msg = "No text extracted from file"
            logger.error(error_msg)
            return {
                "success": False,
                "extracted_text": "",
                "summary": "",
                "model_used": model or provider,
                "skill_used": skill,
                "error": error_msg,
            }

        try:
            prompt_template = _load_summarize_prompt(skill)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load prompt template: {e}")
            return {
                "success": False,
                "extracted_text": extracted_text,
                "summary": "",
                "model_used": model or provider,
                "skill_used": skill,
                "error": f"Prompt template error: {e}",
            }

        def _call_llm(prov: str, mdl: Optional[str]) -> tuple[str, str]:
            if prov == "llamaserver":
                url = f"{settings.llamaserver_url}/v1/chat/completions"
                headers = {"Content-Type": "application/json"}
                if settings.llamaserver_api_key:
                    headers["Authorization"] = f"Bearer {settings.llamaserver_api_key}"
                used = mdl or settings.llamaserver_model
            elif prov == "openrouter":
                if not settings.openrouter_api_key:
                    raise ValueError("OpenRouter API key not configured")
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                }
                used = mdl or settings.openrouter_default_model
            else:
                raise ValueError(f"Unknown provider: {prov}")

            payload = {
                "messages": [
                    {"role": "system", "content": prompt_template},
                    {
                        "role": "user",
                        "content": f"Bitte fasse den folgenden medizinischen Text zusammen:\n\n{extracted_text[:4000]}",
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            }
            if prov != "llamaserver":
                payload["model"] = used

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

            return response.json()["choices"][0]["message"]["content"], used

        used_model: Optional[str] = model
        try:
            try:
                summary, used_model = _call_llm(provider, used_model)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if provider != "llamaserver" or not settings.openrouter_api_key:
                    raise
                logger.warning(
                    f"Llamaserver unreachable ({e}); falling back to OpenRouter ({settings.openrouter_fallback_model})"
                )
                used_model = settings.openrouter_fallback_model
                summary, used_model = _call_llm("openrouter", used_model)

            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Summarization complete in {processing_time:.2f}ms")

            return {
                "success": True,
                "extracted_text": extracted_text,
                "summary": summary,
                "model_used": used_model or provider,
                "skill_used": skill,
                "error": None,
            }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "success": False,
                "extracted_text": extracted_text,
                "summary": "",
                "model_used": used_model or provider,
                "skill_used": skill,
                "error": f"LLM error: {e}",
            }

    except NoOcrBackendError:
        # Propagate so the summarize endpoint can answer 4xx/5xx as appropriate
        raise
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        return {
            "success": False,
            "extracted_text": "",
            "summary": "",
            "model_used": model or provider,
            "skill_used": skill,
            "error": str(e),
        }
