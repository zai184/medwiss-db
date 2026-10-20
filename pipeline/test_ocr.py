"""Tests for the OCR module.

This module contains tests for text extraction from various image formats.
Uses synthetic test images to avoid dependencies on real patient data.
"""

from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from pipeline.ocr import (
    TESSERACT_CONFIG,
    _pdf_to_image,
    extract_text_from_image,
    extract_text_from_images,
    preprocess_image,
)


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image with some text."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)

    # Try to use a basic font, fallback to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    draw.text((10, 10), "Test Text 123", fill="black", font=font)

    image_path = tmp_path / "test_image.png"
    img.save(image_path)
    return image_path


@pytest.fixture
def sample_jpg(tmp_path):
    """Create a sample JPG test image."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    draw.text((10, 10), "JPG Test", fill="black", font=font)

    image_path = tmp_path / "test_image.jpg"
    img.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def grayscale_image():
    """Create a grayscale test image."""
    img = Image.new("L", (100, 100), color=128)
    return img


@pytest.fixture
def color_image():
    """Create a color test image."""
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    return img


class TestPreprocessImage:
    """Tests for image preprocessing function."""

    def test_grayscale_conversion(self, color_image):
        """Test that color images are converted to grayscale."""
        result = preprocess_image(color_image)
        assert result.mode == "L"

    def test_grayscale_passthrough(self, grayscale_image):
        """Test that grayscale images stay grayscale."""
        result = preprocess_image(grayscale_image)
        assert result.mode == "L"

    def test_image_size_preserved(self, color_image):
        """Test that image dimensions are preserved."""
        original_size = color_image.size
        result = preprocess_image(color_image)
        assert result.size == original_size


class TestExtractTextFromImage:
    """Tests for the main OCR extraction function."""

    def test_file_not_found(self):
        """Test handling of non-existent files."""
        with pytest.raises(FileNotFoundError):
            extract_text_from_image("/nonexistent/path/image.png")

    def test_unsupported_format(self, tmp_path):
        """Test handling of unsupported file formats."""
        unsupported_file = tmp_path / "test.gif"
        unsupported_file.write_text("not an image")

        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text_from_image(unsupported_file)

    @patch("pipeline.ocr.pytesseract.image_to_string")
    @patch("pipeline.ocr.preprocess_image")
    def test_successful_png_extraction(
        self, mock_preprocess, mock_tesseract, sample_image, tmp_path
    ):
        """Test successful text extraction from PNG."""
        mock_preprocess.return_value = Image.new("L", (100, 100))
        mock_tesseract.return_value = "Extracted text"

        result = extract_text_from_image(sample_image)

        assert result == "Extracted text"
        mock_tesseract.assert_called_once()
        # Verify German language config is used
        call_args = mock_tesseract.call_args
        assert "deu" in str(call_args)

    @patch("pipeline.ocr.pytesseract.image_to_string")
    @patch("pipeline.ocr.preprocess_image")
    def test_successful_jpg_extraction(self, mock_preprocess, mock_tesseract, sample_jpg):
        """Test successful text extraction from JPG."""
        mock_preprocess.return_value = Image.new("L", (100, 100))
        mock_tesseract.return_value = "JPG extracted"

        result = extract_text_from_image(sample_jpg)

        assert result == "JPG extracted"

    @patch("pipeline.ocr._pdf_to_image")
    @patch("pipeline.ocr.pytesseract.image_to_string")
    @patch("pipeline.ocr.preprocess_image")
    def test_pdf_processing(self, mock_preprocess, mock_tesseract, mock_pdf_to_image, tmp_path):
        """Test PDF processing by converting first page."""
        # Create a dummy PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy content")

        mock_pdf_to_image.return_value = Image.new("RGB", (100, 100))
        mock_preprocess.return_value = Image.new("L", (100, 100))
        mock_tesseract.return_value = "PDF text"

        result = extract_text_from_image(pdf_file)

        assert result == "PDF text"
        mock_pdf_to_image.assert_called_once_with(pdf_file)

    @patch("pipeline.ocr.pytesseract.image_to_string")
    @patch("pipeline.ocr.preprocess_image")
    def test_ocr_failure_handling(self, mock_preprocess, mock_tesseract, sample_image):
        """Test handling of OCR processing failures."""
        mock_preprocess.return_value = Image.new("L", (100, 100))
        mock_tesseract.side_effect = Exception("Tesseract error")

        with pytest.raises(RuntimeError, match="Failed to extract text"):
            extract_text_from_image(sample_image)

    @patch("pipeline.ocr.pytesseract.image_to_string")
    @patch("pipeline.ocr.preprocess_image")
    def test_whitespace_stripping(self, mock_preprocess, mock_tesseract, sample_image):
        """Test that extracted text is properly stripped."""
        mock_preprocess.return_value = Image.new("L", (100, 100))
        mock_tesseract.return_value = "  Text with whitespace  \n\n"

        result = extract_text_from_image(sample_image)

        assert result == "Text with whitespace"


class TestPdfToImage:
    """Tests for PDF to image conversion."""

    def test_pdf2image_not_installed(self, tmp_path):
        """Test handling when pdf2image is not installed."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with patch.dict("sys.modules", {"pdf2image": None}):
            with pytest.raises(ImportError, match="pdf2image is required"):
                _pdf_to_image(pdf_file)

    @patch("pdf2image.convert_from_path")
    def test_successful_conversion(self, mock_convert, tmp_path):
        """Test successful PDF to image conversion."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_image = Image.new("RGB", (100, 100))
        mock_convert.return_value = [mock_image]

        result = _pdf_to_image(pdf_file)

        assert result == mock_image
        mock_convert.assert_called_once_with(pdf_file, first_page=1, last_page=1)

    @patch("pdf2image.convert_from_path")
    def test_empty_pdf_handling(self, mock_convert, tmp_path):
        """Test handling of empty PDFs."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        mock_convert.return_value = []

        with pytest.raises(RuntimeError, match="PDF appears to be empty"):
            _pdf_to_image(pdf_file)


class TestExtractTextFromImages:
    """Tests for batch image processing."""

    @patch("pipeline.ocr.extract_text_from_image")
    def test_batch_processing(self, mock_extract, tmp_path):
        """Test processing multiple images."""
        # Create test files
        img1 = tmp_path / "img1.png"
        img2 = tmp_path / "img2.png"
        img1.write_bytes(b"png data")
        img2.write_bytes(b"png data")

        mock_extract.side_effect = ["Text 1", "Text 2"]

        results = extract_text_from_images([img1, img2])

        assert len(results) == 2
        assert results[str(img1)] == "Text 1"
        assert results[str(img2)] == "Text 2"

    @patch("pipeline.ocr.extract_text_from_image")
    def test_partial_failure_handling(self, mock_extract, tmp_path):
        """Test handling when some images fail."""
        img1 = tmp_path / "img1.png"
        img2 = tmp_path / "img2.png"
        img1.write_bytes(b"png data")
        img2.write_bytes(b"png data")

        mock_extract.side_effect = ["Text 1", RuntimeError("Failed")]

        results = extract_text_from_images([img1, img2])

        assert results[str(img1)] == "Text 1"
        assert "ERROR" in results[str(img2)]


class TestTesseractConfig:
    """Tests for Tesseract configuration."""

    def test_german_language_config(self):
        """Verify German language is configured."""
        assert "deu" in TESSERACT_CONFIG

    def test_oem_psm_config(self):
        """Verify OCR Engine Mode and Page Segmentation Mode are set."""
        assert "--oem 3" in TESSERACT_CONFIG
        assert "--psm 6" in TESSERACT_CONFIG
