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
        "/api/v1/upload_documents/",
        files=[("files", ("test.pdf", file_obj, "application/pdf"))],
    )

    assert response.status_code == 202
    data = response.json()
    assert "1 documents received" in data["message"]
    assert data["tasks"][0]["status"] == "PENDING"
    assert data["tasks"][0]["filename"] == "test.pdf"


def test_upload_invalid_file_type():
    file_content = b"Not a PDF"
    file_obj = io.BytesIO(file_content)

    response = client.post(
        "/api/v1/upload_documents/",
        files=[("files", ("test.txt", file_obj, "text/plain"))],
    )

    assert response.status_code == 400
    assert "Allowed: PDF, PNG, JPG" in response.json()["detail"]


@patch("gateway.api.ingestion.publish_document_event", new_callable=AsyncMock)
@patch("gateway.api.ingestion.upload_file_to_minio")
def test_upload_images_and_multiple_files(mock_upload, mock_publish):
    png_content = b"\x89PNG\x0d\x0a\x1a\x0a"
    jpg_content = b"\xff\xd8\xff\xe0"
    pdf_content = b"%PDF-1.4\n%EOF"

    response = client.post(
        "/api/v1/upload_documents/",
        files=[
            ("files", ("image1.png", io.BytesIO(png_content), "image/png")),
            ("files", ("image2.JPG", io.BytesIO(jpg_content), "image/jpeg")),
            ("files", ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ],
    )

    assert response.status_code == 202
    data = response.json()
    assert "3 documents received" in data["message"]
    assert len(data["tasks"]) == 3
    assert data["tasks"][0]["filename"] == "image1.png"
    assert data["tasks"][1]["filename"] == "image2.JPG"
    assert data["tasks"][2]["filename"] == "doc.pdf"


def test_upload_large_file_rejected():
    # 51 MB of dummy data
    large_content = b"0" * (51 * 1024 * 1024)
    file_obj = io.BytesIO(large_content)

    response = client.post(
        "/api/v1/upload_documents/",
        files=[("files", ("huge.pdf", file_obj, "application/pdf"))],
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"]
