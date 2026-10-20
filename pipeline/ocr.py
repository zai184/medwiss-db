"""OCR module for text extraction from medical images using Tesseract.

This module provides offline OCR capabilities for extracting text from:
- Screenshots (PNG)
- Photos (JPG)
- Scanned documents (PDF)

Uses pytesseract with German language support and basic image preprocessing.
"""

import logging
from pathlib import Path
from typing import Union


try:
    import pytesseract
except ImportError:  # OCR host without tesseract: module stays importable
    pytesseract = None

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Tesseract configuration for German medical text
TESSERACT_CONFIG = r"--oem 3 --psm 6 -l deu"


class OCRDisabledError(RuntimeError):
    """Raised when Tesseract is unavailable (pytesseract not installed).

    Signals the OCR seam to skip this backend and try the next one.
    """


def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR results.

    Applies:
    - Grayscale conversion
    - Contrast enhancement
    - Noise reduction

    Args:
        image: PIL Image object

    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    if image.mode != "L":
        image = image.convert("L")
        logger.debug("Converted image to grayscale")

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    logger.debug("Enhanced contrast")

    # Apply noise reduction
    image = image.filter(ImageFilter.MedianFilter(size=3))
    logger.debug("Applied noise reduction")

    return image


def extract_text_from_image(image_path: Union[str, Path]) -> str:
    """Extract text from an image file using Tesseract OCR.

    Supports PNG, JPG, and PDF files. For PDFs, all pages are processed
    and combined with page separators.

    Args:
        image_path: Path to the image file (PNG, JPG, or PDF)

    Returns:
        Extracted text as string (for PDFs, includes page separators)

    Raises:
        FileNotFoundError: If the image file doesn't exist
        ValueError: If the file format is not supported
        RuntimeError: If OCR processing fails
    """
    image_path = Path(image_path)

    # Validate file exists
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if pytesseract is None:
        raise OCRDisabledError(
            "pytesseract is not installed - OCR unavailable for "
            f"{image_path}"
        )

    # Check file extension
    suffix = image_path.suffix.lower()

    # Validate file format first (don't catch ValueError)
    if suffix == ".pdf":
        # Handle PDF by converting all pages to images
        logger.info(f"Processing PDF: {image_path}")
        try:
            images = _pdf_to_images(image_path)
            # Extract text from all pages
            all_text = []
            for i, image in enumerate(images, 1):
                logger.debug(f"Processing page {i}/{len(images)}...")
                image = preprocess_image(image)
                text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG)
                all_text.append(f"--- Page {i} ---\n{text}")
            full_text = "\n\n".join(all_text)
            logger.info(f"Extracted {len(full_text)} characters from {len(images)} pages of {image_path}")
            return full_text
        except (ImportError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"PDF processing failed for {image_path}: {e}")
            raise RuntimeError(f"Failed to process PDF {image_path}: {e}")
    elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"):
        # Handle image files directly
        logger.info(f"Processing image: {image_path}")
        try:
            image = Image.open(image_path)
        except Exception as e:
            logger.error(f"Failed to open image {image_path}: {e}")
            raise RuntimeError(f"Failed to open image {image_path}: {e}")
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. Supported formats: PNG, JPG, JPEG, BMP, TIFF, PDF"
        )

    # Preprocess image
    logger.debug("Preprocessing image...")
    image = preprocess_image(image)

    # Perform OCR
    logger.debug("Running OCR...")
    try:
        text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG)
    except Exception as e:
        logger.error(f"OCR failed for {image_path}: {e}")
        raise RuntimeError(f"OCR processing failed for {image_path}: {e}")

    # Clean up extracted text
    text = text.strip()

    logger.info(f"Extracted {len(text)} characters from {image_path}")

    return text


def _pdf_to_images(pdf_path: Path) -> list[Image.Image]:
    """Convert all pages of PDF to PIL Images.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of PIL Images (one per page)

    Raises:
        ImportError: If pdf2image is not installed
        RuntimeError: If conversion fails
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image is required for PDF processing. Install with: pip install pdf2image"
        )

    try:
        # Convert ALL pages (no page limits)
        images = convert_from_path(pdf_path)
        if not images:
            raise RuntimeError("PDF appears to be empty or unreadable")
        return images
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF to images: {e}")


def extract_text_from_images(image_paths: list[Union[str, Path]]) -> dict[str, str]:
    """Extract text from multiple images.

    Args:
        image_paths: List of paths to image files

    Returns:
        Dictionary mapping file paths to extracted text
    """
    results = {}

    for path in image_paths:
        try:
            text = extract_text_from_image(path)
            results[str(path)] = text
        except Exception as e:
            logger.error(f"Failed to process {path}: {e}")
            results[str(path)] = f"[ERROR: {e}]"

    return results
