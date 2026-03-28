import pytest
from fastapi.testclient import TestClient
from gateway.main import app
from gateway.api.deps import get_db
from shared.models import DBUser
from gateway.core.security import get_password_hash


async def override_get_db():
    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            # Return a mock DBUser that matches the test expectation
                            return DBUser(
                                id=1,
                                email="test@example.com",
                                hashed_password=get_password_hash("password123"),
                                full_name="Test User",
                                is_active=True,
                            )

                    return MockScalars()

            return MockResult()

    yield MockSession()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_login_success_generates_token():
    # Expected behavior: POST to login with form data returns JWT
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_protected_route_requires_token():
    # Expected behavior: Missing Authorization header results in 401 Unauthorized
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_valid_token_dependency_injection():
    # We need a token first
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )

    # If login fails (not implemented yet), stop test here (TDD cycle)
    if login_resp.status_code != 200:
        pytest.fail("Login endpoint not yet implemented")

    token = login_resp.json()["access_token"]

    # Inject token into header
    headers = {"Authorization": f"Bearer {token}"}
    protected_resp = client.get("/api/v1/users/me", headers=headers)

    assert protected_resp.status_code == 200
    assert protected_resp.json()["email"] == "test@example.com"
