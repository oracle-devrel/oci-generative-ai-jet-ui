"""Integration tests for user API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestUserEndpoints:
    """Tests for /api/v1/users endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fittrack.main import create_app

        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        with patch("fittrack.api.routes.users.UserRepository") as mock:
            repo_instance = MagicMock()
            mock.return_value = repo_instance
            yield repo_instance

    def test_list_users_returns_paginated_list(self, client, mock_user_repo):
        """GET /api/v1/users returns paginated user list."""
        mock_user_repo.find_all.return_value = [
            {"_id": "1", "email": "test1@example.com", "status": "active"},
            {"_id": "2", "email": "test2@example.com", "status": "active"},
        ]
        mock_user_repo.count.return_value = 2

        response = client.get("/api/v1/users")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 2

    def test_list_users_with_pagination_params(self, client, mock_user_repo):
        """GET /api/v1/users accepts pagination parameters."""
        mock_user_repo.find_all.return_value = []
        mock_user_repo.count.return_value = 0

        response = client.get("/api/v1/users?page=2&limit=10")

        assert response.status_code == 200
        mock_user_repo.find_all.assert_called_once()
        call_kwargs = mock_user_repo.find_all.call_args[1]
        assert call_kwargs["offset"] == 10  # (page-1) * limit
        assert call_kwargs["limit"] == 10

    def test_get_user_by_id(self, client, mock_user_repo):
        """GET /api/v1/users/{id} returns single user."""
        mock_user_repo.find_by_id.return_value = {
            "_id": "123",
            "email": "test@example.com",
            "status": "active",
            "role": "user",
            "email_verified": False,
            "point_balance": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        response = client.get("/api/v1/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_get_user_not_found(self, client, mock_user_repo):
        """GET /api/v1/users/{id} returns 404 when not found."""
        mock_user_repo.find_by_id.return_value = None

        response = client.get("/api/v1/users/nonexistent")

        assert response.status_code == 404

    def test_create_user(self, client, mock_user_repo):
        """POST /api/v1/users creates a new user."""
        mock_user_repo.find_by_email.return_value = None
        mock_user_repo.create.return_value = {
            "_id": "new-id",
            "email": "new@example.com",
            "status": "pending",
            "role": "user",
            "email_verified": False,
            "point_balance": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        response = client.post(
            "/api/v1/users",
            json={"email": "new@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"

    def test_create_user_duplicate_email(self, client, mock_user_repo):
        """POST /api/v1/users returns 409 for duplicate email."""
        mock_user_repo.find_by_email.return_value = {
            "_id": "existing",
            "email": "existing@example.com",
        }

        response = client.post(
            "/api/v1/users",
            json={"email": "existing@example.com", "password": "securepassword123"},
        )

        assert response.status_code == 409

    def test_update_user(self, client, mock_user_repo):
        """PUT /api/v1/users/{id} updates user."""
        mock_user_repo.find_by_id.return_value = {
            "_id": "123",
            "email": "test@example.com",
            "status": "active",
            "role": "user",
        }
        mock_user_repo.update.return_value = True

        response = client.put(
            "/api/v1/users/123",
            json={"status": "suspended"},
        )

        assert response.status_code == 200

    def test_delete_user(self, client, mock_user_repo):
        """DELETE /api/v1/users/{id} deletes user."""
        mock_user_repo.find_by_id.return_value = {"_id": "123"}
        mock_user_repo.delete.return_value = True

        response = client.delete("/api/v1/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True


class TestUserValidation:
    """Tests for user input validation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fittrack.main import create_app

        app = create_app()
        return TestClient(app)

    def test_create_user_invalid_email(self, client):
        """POST /api/v1/users rejects invalid email."""
        response = client.post(
            "/api/v1/users",
            json={"email": "not-an-email", "password": "securepassword123"},
        )

        assert response.status_code == 422

    def test_create_user_short_password(self, client):
        """POST /api/v1/users rejects short password."""
        response = client.post(
            "/api/v1/users",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422
