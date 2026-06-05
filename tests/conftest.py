"""
Test fixtures for Recipe Explorer tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_storage, get_mealdb_adapter, get_current_user, verify_csrf_token
from app.services.storage import RecipeStorage
from app.models import User


class FakeMealDBAdapter:
    """Mock adapter for TheMealDB API, preventing actual HTTP calls in tests."""

    async def search_by_name(self, name: str):
        if not name or not name.strip():
            return [], False
        # Match "chicken" to satisfy test_unified_search_timing_headers & test_unified_search_x_cache_header
        if "chicken" in name.lower() or "curry" in name.lower():
            return [
                {
                    "id": "mealdb-52771",
                    "title": "Spicy Arrabiata Penne",
                    "description": "A test recipe from TheMealDB",
                    "ingredients": ["penne", "sauce"],
                    "instructions": ["Cook pasta", "Add sauce"],
                    "tags": ["pasta"],
                    "cuisine": "Italian",
                    "source": "external",
                }
            ], True  # cache hit
        return [], False

    async def get_by_id(self, meal_id: str):
        if meal_id == "52771":
            return {
                "id": "mealdb-52771",
                "title": "Spicy Arrabiata Penne",
                "description": "A test recipe from TheMealDB",
                "ingredients": ["penne", "sauce"],
                "instructions": ["Cook pasta", "Add sauce"],
                "tags": ["pasta"],
                "cuisine": "Italian",
                "source": "external",
            }
        return None


@pytest.fixture
def test_storage():
    """Create a fresh RecipeStorage instance for a test"""
    return RecipeStorage()


@pytest.fixture(autouse=True)
def override_dependencies(test_storage):
    """Override standard dependencies with test-isolated implementations."""
    app.dependency_overrides[get_storage] = lambda: test_storage
    app.dependency_overrides[get_mealdb_adapter] = FakeMealDBAdapter
    
    # Provide a default mock authenticated user for backward compatibility of recipe CRUD tests
    mock_user = User(
        id="test-user-id",
        username="testuser",
        email="testuser@example.com",
        password_hash="mock_hash",
        profile_name="Test User",
        preferences={}
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[verify_csrf_token] = lambda: None
    
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Test client for making requests to the API"""
    return TestClient(app)


@pytest.fixture
def clean_storage(test_storage):
    """Reset storage before and after each test"""
    test_storage.recipes.clear()
    yield
    test_storage.recipes.clear()


@pytest.fixture
def sample_recipe_data():
    """Sample recipe for testing"""
    return {
        "title": "Test Recipe",
        "description": "A test recipe",
        "ingredients": ["ingredient 1", "ingredient 2"],
        "instructions": ["First, do step 1.", "Then, do step 2."],
        "tags": ["test"],
        "cuisine": "Global",
    }
