"""Tests for processing.services.db_client with mocked SQLAlchemy engine and session."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_db_creates_extension_and_tables():
    """init_db runs CREATE EXTENSION and create_all against the engine."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_engine = MagicMock()
    mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_base = MagicMock()

    with patch(
        "processing.services.db_client.get_db_components",
        return_value=(mock_engine, None),
    ), patch("processing.services.db_client.Base", mock_base):
        from processing.services.db_client import init_db

        await init_db()

    mock_conn.execute.assert_called_once()
    mock_conn.run_sync.assert_called_once()


# ---------------------------------------------------------------------------
# store_document_chunks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_document_chunks_adds_and_commits():
    """store_document_chunks adds one DocumentChunk per chunk and commits."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)

    fake_chunks = ["chunk one", "chunk two"]
    fake_embeddings = [[0.1] * 768, [0.2] * 768]
    fake_entities = [[{"text": "Apple", "label": "ORG"}], []]

    with patch(
        "processing.services.db_client.get_db_components",
        return_value=(None, mock_session_factory),
    ):
        from processing.services.db_client import store_document_chunks

        await store_document_chunks(
            document_id="doc-123",
            tenant_id="user@example.com",
            filename="report.pdf",
            chunks=fake_chunks,
            embeddings=fake_embeddings,
            entities_list=fake_entities,
        )

    assert mock_session.add.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_document_chunks_empty_input():
    """store_document_chunks with no chunks still commits (no-op)."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "processing.services.db_client.get_db_components",
        return_value=(None, MagicMock(return_value=mock_session)),
    ):
        from processing.services.db_client import store_document_chunks

        await store_document_chunks("d", "t", "f.pdf", [], [], [])

    mock_session.add.assert_not_called()
    mock_session.commit.assert_awaited_once()
