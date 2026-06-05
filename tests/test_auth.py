"""
Tests for authentication flow.
"""

import pytest
from app.services.auth import verify_password, hash_password
from app.dependencies import get_current_user
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def enable_real_auth():
    """Clear conftest overrides of get_current_user to run real authentication checks."""
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    yield
    # Restore bypass for other tests
    mock_user = User(
        id="test-user-id",
        username="testuser",
        email="testuser@example.com",
        password_hash="mock_hash",
        profile_name="Test User",
        preferences={}
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user


def test_password_hashing():
    """Verify that password hashing and verification works using scrypt."""
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    
    assert hashed.startswith("scrypt$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_register_flow(client):
    """Test register endpoint works and sets cookies."""
    payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "mypassword123",
        "profile_name": "Test User Display"
    }
    
    response = client.post("https://testserver/api/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert data["profile_name"] == "Test User Display"
    
    # Check that secure session and CSRF cookies are set
    cookies = response.cookies
    assert "__Secure-session" in cookies
    assert "csrf_token" in cookies


def test_register_validation(client):
    """Test input validation for register endpoint."""
    # Password too short
    payload = {
        "username": "baduser",
        "email": "test@example.com",
        "password": "short",
    }
    response = client.post("https://testserver/api/auth/register", json=payload)
    assert response.status_code == 422
    
    # Invalid email format
    payload = {
        "username": "baduser",
        "email": "not-an-email",
        "password": "longenoughpwd",
    }
    response = client.post("https://testserver/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_logout_flow(client):
    """Test register, login, and logout flow."""
    # Register user
    reg_response = client.post("https://testserver/api/auth/register", json={
        "username": "loguser",
        "email": "loguser@example.com",
        "password": "securepassword"
    })
    assert reg_response.status_code == 201
    
    # Logout to clear active session cookies
    logout_res1 = client.post("https://testserver/api/auth/logout")
    assert logout_res1.status_code == 200
    
    # Try to log in
    response = client.post("https://testserver/api/auth/login", json={
        "username": "loguser",
        "password": "securepassword"
    })
    assert response.status_code == 200
    assert "__Secure-session" in response.cookies
    
    # Check user profile retrieval
    me_res = client.get("https://testserver/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "loguser"
    
    # Logout
    logout_res = client.post("https://testserver/api/auth/logout")
    assert logout_res.status_code == 200
    
    # Verify me endpoint is now blocked
    me_res2 = client.get("https://testserver/api/auth/me")
    assert me_res2.status_code == 401
