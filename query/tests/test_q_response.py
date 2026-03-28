from unittest.mock import patch
from fastapi.testclient import TestClient
from gateway.main import app
from shared.models import DocumentChunk
from gateway.api.deps import get_current_user
from gateway.models.user import User

client = TestClient(app)


@patch("query.api.q_response.get_embeddings")
@patch("query.api.q_response.retrieve_relevant_chunks")
@patch("query.api.q_response.generate_rag_answer")
def test_ask_question_endpoint(mock_gen_ans, mock_ret_chunks, mock_get_embed):
    # Mock authentication
    mock_user = User(id=1, email="test@tenant.com", full_name="Test User")

    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Mock embeddings to avoid hitting the API or downloading models locally
    async def mock_embed(*args, **kwargs):
        return [[0.0] * 768]

    mock_get_embed.side_effect = mock_embed
    # Mock chunks returned by retrieval
    mock_chunk = DocumentChunk(
        document_id="doc_1",
        tenant_id="test@tenant.com",
        filename="doc1.pdf",
        chunk_index=0,
        text_content="content of test doc",
        entities=[{"text": "Apple Inc."}],
        embedding=[0.0] * 768,
    )

    # Needs to be async compatible mock return
    async def mock_retrieve(*args, **kwargs):
        return [(mock_chunk, 0.05)]

    mock_ret_chunks.side_effect = mock_retrieve

    # Mock LLM response
    async def mock_answer(*args, **kwargs):
        return "Detailed RAG Answer"

    mock_gen_ans.side_effect = mock_answer

    # Act
    payload = {
        "question": "What is the capital of France?",
        "top_k": 3,
        "filter": {"tenant_id": "test_tenant"},
    }
    response = client.post("/api/v1/query/", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Detailed RAG Answer"
    assert data["confidence_score"] == 0.95
    assert len(data["quoted_sources"]) == 1
    assert data["quoted_sources"][0]["document_id"] == "doc_1"
    assert data["quoted_sources"][0]["filename"] == "doc1.pdf"
    assert "Apple Inc." in data["detected_entities"]

    # Cleanup overrides
    app.dependency_overrides = {}


@patch("query.api.q_response.get_embeddings")
@patch("query.api.q_response.retrieve_relevant_chunks")
def test_ask_question_endpoint_error_handling(mock_ret_chunks, mock_get_embed):
    # Mock authentication
    mock_user = User(id=1, email="test@tenant.com", full_name="Test User")

    async def mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    async def mock_embed(*args, **kwargs):
        return [[0.0] * 768]

    mock_get_embed.side_effect = mock_embed

    # Make retrieve chunks throw an unexpected exception
    async def raise_error(*args, **kwargs):
        raise ValueError("Database failure mock")

    mock_ret_chunks.side_effect = raise_error

    payload = {"question": "What happens on error?", "top_k": 5}
    response = client.post("/api/v1/query/", json=payload)

    assert response.status_code == 500
    assert "Failed to process query" in response.json()["detail"]

    # Cleanup overrides
    app.dependency_overrides = {}
