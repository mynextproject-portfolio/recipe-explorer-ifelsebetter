"""
Tests for Double-Submit CSRF token validation.
"""

import pytest
from app.dependencies import verify_csrf_token
from app.main import app


@pytest.fixture
def enable_csrf():
    """Fixture to restore the real CSRF dependency for testing."""
    # Remove conftest.py override of verify_csrf_token
    if verify_csrf_token in app.dependency_overrides:
        del app.dependency_overrides[verify_csrf_token]
    yield
    # Re-apply bypass override after test finishes
    app.dependency_overrides[verify_csrf_token] = lambda: None


def test_csrf_missing(client, enable_csrf, sample_recipe_data):
    """POST request without CSRF cookies or headers should be rejected with 403."""
    response = client.post("/api/recipes", json=sample_recipe_data)
    assert response.status_code == 403
    assert "CSRF token mismatch" in response.json()["detail"]


def test_csrf_mismatch(client, enable_csrf, sample_recipe_data):
    """POST request with mismatched cookie/header CSRF tokens should be rejected with 403."""
    client.cookies.set("csrf_token", "cookie_value_123")
    response = client.post(
        "/api/recipes",
        json=sample_recipe_data,
        headers={"X-CSRF-Token": "different_header_value"}
    )
    assert response.status_code == 403


def test_csrf_success(client, enable_csrf, sample_recipe_data):
    """POST request with matching cookie and header CSRF tokens should be allowed."""
    token = "matching_token_abc"
    client.cookies.set("csrf_token", token)
    response = client.post(
        "/api/recipes",
        json=sample_recipe_data,
        headers={"X-CSRF-Token": token}
    )
    # The endpoint should process normally (201 Created or normal validations)
    assert response.status_code == 201
