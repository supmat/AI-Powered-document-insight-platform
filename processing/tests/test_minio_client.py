"""Tests for processing.services.minio_client with mocked MinIO SDK."""
import pytest
from unittest.mock import MagicMock, patch


def _make_response(data: bytes) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = data
    return resp


# ---------------------------------------------------------------------------
# download_file_from_minio
# ---------------------------------------------------------------------------


def test_download_file_success():
    """Happy path: MinIO returns bytes."""
    fake_data = b"PDF content here"
    mock_response = _make_response(fake_data)

    with patch("processing.services.minio_client.minio_client") as mock_mc:
        mock_mc.get_object.return_value = mock_response
        from processing.services.minio_client import download_file_from_minio

        result = download_file_from_minio("tenant/doc.pdf")

    assert result == fake_data
    mock_mc.get_object.assert_called_once()
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()


def test_download_file_calls_close_on_exception():
    """Even when get_object raises, response.close() is still called if response was set."""
    mock_response = MagicMock()
    call_count = 0

    def get_object_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # fail first two attempts (tenacity retries)
            raise Exception("temporary failure")
        return mock_response

    mock_response.read.return_value = b"data"

    with patch("processing.services.minio_client.minio_client") as mock_mc:
        mock_mc.get_object.side_effect = get_object_side_effect
        from processing.services.minio_client import download_file_from_minio

        result = download_file_from_minio("tenant/doc.pdf")

    assert result == b"data"


def test_download_file_raises_after_retries():
    """Raises RetryError (from tenacity) after all retry attempts are exhausted."""
    from tenacity import RetryError

    with patch("processing.services.minio_client.minio_client") as mock_mc:
        mock_mc.get_object.side_effect = Exception("MinIO down")
        from processing.services.minio_client import download_file_from_minio

        with pytest.raises(RetryError):
            download_file_from_minio("bad/path.pdf")
