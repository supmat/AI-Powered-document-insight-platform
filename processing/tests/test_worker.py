"""Tests for the process_message() worker function in processing.main."""
import json
import pytest
import fitz
from unittest.mock import AsyncMock, MagicMock, patch


def _make_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sample worker test text for processing")
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def _build_message(payload: dict) -> MagicMock:
    """Build a minimal aio_pika message mock."""
    msg = MagicMock()
    msg.body = json.dumps(payload).encode()
    # process() context manager — just yields control
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=None)
    ctx.__aexit__ = AsyncMock(return_value=False)
    msg.process.return_value = ctx
    return msg


# ---------------------------------------------------------------------------
# PDF processing path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_pdf_happy_path():
    """PDF message: download → extract → chunk → embed → store."""
    payload = {
        "document_id": "doc-001",
        "tenant_id": "user@test.com",
        "file_path": "user@test.com/doc-001_report.pdf",
    }
    message = _build_message(payload)

    fake_embeddings = [[0.1] * 768]

    with patch(
        "processing.main.download_file_from_minio", return_value=_make_pdf_bytes()
    ), patch(
        "processing.main.get_embeddings", AsyncMock(return_value=fake_embeddings)
    ), patch(
        "processing.main.store_document_chunks", AsyncMock()
    ) as mock_store:
        from processing.main import process_message

        await process_message(message)

    mock_store.assert_awaited_once()
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["document_id"] == "doc-001"
    assert call_kwargs["tenant_id"] == "user@test.com"
    assert call_kwargs["filename"] == "doc-001_report.pdf"


# ---------------------------------------------------------------------------
# Image processing path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_image_happy_path():
    """Image (jpg) message: delegates text extraction to image extractor."""
    payload = {
        "document_id": "doc-002",
        "tenant_id": "user@test.com",
        "file_path": "user@test.com/doc-002_scan.jpg",
    }
    message = _build_message(payload)

    with patch(
        "processing.main.download_file_from_minio", return_value=b"fake-image-bytes"
    ), patch(
        "processing.main.extract_text_from_image",
        AsyncMock(return_value="Image text content"),
    ), patch(
        "processing.main.get_embeddings", AsyncMock(return_value=[[0.1] * 768])
    ), patch(
        "processing.main.store_document_chunks", AsyncMock()
    ) as mock_store:
        from processing.main import process_message

        await process_message(message)

    mock_store.assert_awaited_once()


# ---------------------------------------------------------------------------
# Empty text → skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_skips_empty_text():
    """When extracted text is empty, store_document_chunks is never called."""
    payload = {
        "document_id": "doc-003",
        "tenant_id": "user@test.com",
        "file_path": "user@test.com/doc-003_blank.pdf",
    }
    message = _build_message(payload)

    with patch("processing.main.download_file_from_minio", return_value=b"pdf"), patch(
        "processing.main.extract_text_from_pdf", return_value=""
    ), patch("processing.main.store_document_chunks", AsyncMock()) as mock_store:
        from processing.main import process_message

        await process_message(message)

    mock_store.assert_not_awaited()


# ---------------------------------------------------------------------------
# Unknown file extension
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_unknown_extension_does_not_crash():
    """Unknown extension raises ValueError internally; process_message catches it gracefully."""
    payload = {
        "document_id": "doc-004",
        "tenant_id": "user@test.com",
        "file_path": "user@test.com/doc-004_file.txt",
    }
    message = _build_message(payload)

    with patch(
        "processing.main.download_file_from_minio", return_value=b"text data"
    ), patch("processing.main.store_document_chunks", AsyncMock()) as mock_store:
        from processing.main import process_message

        # Should NOT raise — exception is caught inside process_message
        await process_message(message)

    mock_store.assert_not_awaited()


# ---------------------------------------------------------------------------
# Download failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_download_failure_is_handled():
    """If MinIO download fails, message processing exits cleanly without crashing."""
    payload = {
        "document_id": "doc-005",
        "tenant_id": "user@test.com",
        "file_path": "user@test.com/doc-005_missing.pdf",
    }
    message = _build_message(payload)

    with patch(
        "processing.main.download_file_from_minio", side_effect=Exception("MinIO error")
    ), patch("processing.main.store_document_chunks", AsyncMock()) as mock_store:
        from processing.main import process_message

        await process_message(message)

    mock_store.assert_not_awaited()
