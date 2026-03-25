"""Tests for processing.services.gemini_client with mocked Gemini API and SentenceTransformer."""
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_embedding_result(n: int = 1) -> MagicMock:
    """Return a mock result whose .embeddings list contains n embedding objects."""
    result = MagicMock()
    result.embeddings = [MagicMock(values=[0.1] * 768) for _ in range(n)]
    return result


# ---------------------------------------------------------------------------
# Tests: Gemini path (client exists)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_embeddings_via_gemini():
    """Happy path: Gemini client exists and returns embeddings."""
    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = _fake_embedding_result(2)

    with patch("processing.services.gemini_client._client", mock_client):
        from processing.services.gemini_client import get_embeddings

        result = await get_embeddings(["hello", "world"])

    assert len(result) == 2
    assert len(result[0]) == 768


@pytest.mark.asyncio
async def test_get_embeddings_gemini_falls_back_on_exception():
    """When Gemini raises, falls back to local SentenceTransformer."""
    import numpy as np

    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = Exception("API error")

    mock_embedder = MagicMock()
    mock_embedder.encode.return_value = np.array([[0.2] * 768])

    with patch("processing.services.gemini_client._client", mock_client), patch(
        "processing.services.gemini_client.local_embedder", mock_embedder
    ):
        from processing.services.gemini_client import get_embeddings

        result = await get_embeddings(["hello"])

    assert len(result) == 1
    assert len(result[0]) == 768


# ---------------------------------------------------------------------------
# Tests: local fallback path (no Gemini client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_embeddings_local_fallback_no_client():
    """When _client is None, uses SentenceTransformer directly."""
    import numpy as np

    mock_embedder = MagicMock()
    mock_embedder.encode.return_value = np.array([[0.3] * 768, [0.4] * 768])

    with patch("processing.services.gemini_client._client", None), patch(
        "processing.services.gemini_client.local_embedder", mock_embedder
    ):
        from processing.services.gemini_client import get_embeddings

        result = await get_embeddings(["foo", "bar"])

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_embeddings_initializes_local_model_when_none():
    """When local_embedder is None and _client is None, loads SentenceTransformer."""
    import numpy as np

    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.5] * 768])

    with patch("processing.services.gemini_client._client", None), patch(
        "processing.services.gemini_client.local_embedder", None
    ), patch(
        "processing.services.gemini_client.SentenceTransformer", return_value=mock_model
    ):
        from processing.services.gemini_client import get_embeddings

        result = await get_embeddings(["init test"])

    assert len(result) == 1
