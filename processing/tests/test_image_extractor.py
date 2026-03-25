"""Tests for processing.services.image_extractor with mocked Gemini and EasyOCR."""
import io
import pytest
import numpy as np
from PIL import Image
from unittest.mock import AsyncMock, MagicMock, patch


# Create a minimal valid PNG in memory to use as test input.
def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


PNG_BYTES = _make_png_bytes()


# ---------------------------------------------------------------------------
# Gemini Vision path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_via_gemini():
    """When _client is set, uses Gemini Vision and returns its text."""
    mock_response = MagicMock()
    mock_response.text = "Extracted via Gemini"

    mock_aio = AsyncMock()
    mock_aio.models.generate_content = AsyncMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.aio = mock_aio

    with patch("processing.services.image_extractor._client", mock_client):
        from processing.services.image_extractor import extract_text_from_image

        result = await extract_text_from_image(PNG_BYTES)

    assert result == "Extracted via Gemini"


@pytest.mark.asyncio
async def test_extract_text_gemini_falls_back_to_easyocr():
    """When Gemini raises, falls back to EasyOCR."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("API error")
    )

    mock_reader = MagicMock()
    mock_reader.readtext.return_value = ["Hello", "World"]

    # Patch cv2 to avoid GPU/hardware dependency
    mock_cv2 = MagicMock()
    mock_cv2.imdecode.return_value = np.zeros((64, 64, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((64, 64), dtype=np.uint8)
    mock_cv2.GaussianBlur.return_value = np.zeros((64, 64), dtype=np.uint8)
    mock_cv2.threshold.return_value = (0, np.zeros((64, 64), dtype=np.uint8))
    mock_cv2.COLOR_BGR2GRAY = 6
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.THRESH_BINARY = 0
    mock_cv2.THRESH_OTSU = 8

    with patch("processing.services.image_extractor._client", mock_client), patch(
        "processing.services.image_extractor.ocr_reader", mock_reader
    ), patch("processing.services.image_extractor.cv2", mock_cv2):
        from processing.services.image_extractor import extract_text_from_image

        result = await extract_text_from_image(PNG_BYTES)

    assert result == "Hello World"


# ---------------------------------------------------------------------------
# EasyOCR-only path (no Gemini client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_easyocr_only():
    """When _client is None, goes directly to EasyOCR."""
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = ["OCR", "result"]

    mock_cv2 = MagicMock()
    mock_cv2.imdecode.return_value = np.zeros((64, 64, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((64, 64), dtype=np.uint8)
    mock_cv2.GaussianBlur.return_value = np.zeros((64, 64), dtype=np.uint8)
    mock_cv2.threshold.return_value = (0, np.zeros((64, 64), dtype=np.uint8))
    mock_cv2.COLOR_BGR2GRAY = 6
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.THRESH_BINARY = 0
    mock_cv2.THRESH_OTSU = 8

    with patch("processing.services.image_extractor._client", None), patch(
        "processing.services.image_extractor.ocr_reader", mock_reader
    ), patch("processing.services.image_extractor.cv2", mock_cv2):
        from processing.services.image_extractor import extract_text_from_image

        result = await extract_text_from_image(PNG_BYTES)

    assert result == "OCR result"
