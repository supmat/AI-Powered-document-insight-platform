from fastapi.testclient import TestClient
from gateway.main import app
from gateway.api.deps import get_current_user
from gateway.models.user import User
from unittest.mock import patch, AsyncMock
import io


import pytest

client = TestClient(app)


# Mock authenticated user
async def override_get_current_user():
    return User(id=1, email="test@example.com", full_name="Test User", roles=["user"])


@pytest.fixture(autouse=True)
def override_auth_for_ingestion():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@patch("gateway.api.ingestion.publish_document_event", new_callable=AsyncMock)
@patch("gateway.api.ingestion.upload_file_to_minio")
def test_upload_pdf_success(mock_upload, mock_publish):
    # Dummy PDF file content
    file_content = b"%PDF-1.4\n%EOF"
    file_obj = io.BytesIO(file_content)

    response = client.post(
        "/api/v1/documents/", files={"file": ("test.pdf", file_obj, "application/pdf")}
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["filename"] == "test.pdf"
    assert "task_id" in data


def test_upload_invalid_file_type():
    file_content = b"Not a PDF"
    file_obj = io.BytesIO(file_content)

    response = client.post(
        "/api/v1/documents/", files={"file": ("test.txt", file_obj, "text/plain")}
    )

    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]
