"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    from fittrack.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    from fastapi.testclient import TestClient

    return TestClient(app)


# Mark all tests in unit/ as unit tests
def pytest_collection_modifyitems(config, items):
    """Add markers based on test location."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
