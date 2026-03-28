import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from query.services.gemini_client import retrieve_relevant_chunks, generate_rag_answer
from processing.core.database import DocumentChunk


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Mock the execute result
    result = MagicMock()

    chunk = DocumentChunk(
        document_id="123",
        tenant_id="tenant1",
        filename="test.pdf",
        chunk_index=0,
        text_content="This is a test chunk context.",
        entities=[{"text": "test_entity"}],
        embedding=[0.1] * 768,
    )
    result.all.return_value = [(chunk, 0.1)]
    session.execute.return_value = result
    return session


@pytest.mark.asyncio
async def test_retrieve_relevant_chunks(mock_db_session):
    chunks = await retrieve_relevant_chunks(
        db=mock_db_session,
        question_embedding=[0.1] * 768,
        filters={"tenant_id": "tenant1"},
        top_k=5,
    )
    assert len(chunks) == 1
    # Result from result.all() is list of tuples (chunk, distance)
    chunk, dist = chunks[0]
    assert chunk.tenant_id == "tenant1"
    assert chunk.text_content == "This is a test chunk context."


@pytest.mark.asyncio
async def test_generate_rag_answer_empty_chunks():
    ans = await generate_rag_answer("What is life?", [])
    assert "could not find any relevant documents" in ans


@pytest.mark.asyncio
@patch("query.services.gemini_client._client")
async def test_generate_rag_answer_gemini_success(mock_client):
    mock_response = MagicMock()
    mock_response.text = "Gemini answer!"
    mock_client.models.generate_content.return_value = mock_response

    chunk = DocumentChunk(
        text_content="Sample context content",
        filename="t.pdf",
        document_id="1",
        tenant_id="a",
        chunk_index=0,
        embedding=[0.0] * 768,
    )

    ans = await generate_rag_answer("Query?", [chunk])
    assert ans == "Gemini answer!"


@pytest.mark.asyncio
@patch("query.services.gemini_client._generate_local_answer")
@patch("query.services.gemini_client._client", None)
async def test_generate_rag_answer_local_fallback(mock_local):
    mock_local.return_value = "Local Model Answer!"

    chunk = DocumentChunk(
        text_content="Sample context content",
        filename="t.pdf",
        document_id="1",
        tenant_id="a",
        chunk_index=0,
        embedding=[0.0] * 768,
    )

    ans = await generate_rag_answer("Query?", [chunk])
    assert ans == "Local Model Answer!"


def test_generate_local_answer_mocked_pipeline():
    mock_transformers = MagicMock()
    mock_pipeline_func = MagicMock()
    mock_llm = MagicMock()
    mock_llm.return_value = [{"generated_text": "Mocked pipeline answer"}]
    mock_pipeline_func.return_value = mock_llm
    mock_transformers.pipeline = mock_pipeline_func

    with patch.dict("sys.modules", {"transformers": mock_transformers}):
        # Reset global to trigger init
        import query.services.gemini_client as gc

        gc._local_llm_pipeline = None

        ans = gc._generate_local_answer("Hello")
        assert ans == "Mocked pipeline answer"
        mock_pipeline_func.assert_called_once()


def _fake_embedding_result(n: int = 1) -> MagicMock:
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

    with patch("query.services.gemini_client._client", mock_client):
        from query.services.gemini_client import get_embeddings

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

    with patch("query.services.gemini_client._client", mock_client), patch(
        "query.services.gemini_client.local_embedder", mock_embedder
    ):
        from query.services.gemini_client import get_embeddings

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

    with patch("query.services.gemini_client._client", None), patch(
        "query.services.gemini_client.local_embedder", mock_embedder
    ):
        from query.services.gemini_client import get_embeddings

        result = await get_embeddings(["foo", "bar"])

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_embeddings_initializes_local_model_when_none():
    """When local_embedder is None and _client is None, loads SentenceTransformer."""
    import numpy as np

    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.5] * 768])

    with patch("query.services.gemini_client._client", None), patch(
        "query.services.gemini_client.local_embedder", None
    ), patch(
        "query.services.gemini_client.SentenceTransformer", return_value=mock_model
    ):
        from query.services.gemini_client import get_embeddings

        result = await get_embeddings(["init test"])

    assert len(result) == 1
