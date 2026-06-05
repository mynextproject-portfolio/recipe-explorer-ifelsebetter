import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_storage
from app.services.sqlite_storage import SQLiteRecipeStorage

@pytest.fixture
def sqlite_test_storage():
    # Setup temporary db file
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    storage = SQLiteRecipeStorage(db_path=path)
    
    # Insert mock user so FOREIGN KEY constraint doesn't fail during test runs
    import sqlite3
    conn = sqlite3.connect(path)
    # Insert test user
    conn.execute(
        """
        INSERT INTO users (id, username, email, password_hash, profile_name, preferences, created_at, updated_at)
        VALUES ('test-user-id', 'testuser', 'testuser@example.com', 'mock_hash', 'Test User', '{}', '2026-06-05T00:00:00', '2026-06-05T00:00:00')
        """
    )
    conn.commit()
    conn.close()
    
    yield storage
    
    # Teardown
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def sqlite_client(sqlite_test_storage):
    # Override only get_storage with our temporary SQLiteRecipeStorage instance
    app.dependency_overrides[get_storage] = lambda: sqlite_test_storage
    client = TestClient(app)
    yield client
    # Clean up overrides after test
    app.dependency_overrides.clear()

def test_api_sqlite_create_and_get(sqlite_client):
    recipe_data = {
        "title": "SQL Integration Pizza",
        "description": "Crispy base",
        "ingredients": ["dough", "tomato sauce", "mozzarella"],
        "instructions": ["Roll dough", "Spread sauce", "Bake"],
        "tags": ["pizza", "cheese"],
        "cuisine": "Italian"
    }
    
    # Post recipe
    response = sqlite_client.post("/api/recipes", json=recipe_data)
    assert response.status_code == 201
    created = response.json()
    assert "id" in created
    assert created["title"] == "SQL Integration Pizza"
    
    # Get recipe
    get_response = sqlite_client.get(f"/api/recipes/{created['id']}")
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["id"] == created["id"]
    assert retrieved["title"] == "SQL Integration Pizza"
    assert retrieved["ingredients"] == ["dough", "tomato sauce", "mozzarella"]
    assert retrieved["tags"] == ["pizza", "cheese"]

def test_api_sqlite_search(sqlite_client):
    # Add a couple of recipes
    r1 = sqlite_client.post("/api/recipes", json={
        "title": "Garlic Bread",
        "description": "Garlicky",
        "ingredients": ["bread", "garlic", "butter"],
        "instructions": ["Spread garlic butter on bread", "Toast"],
        "tags": ["appetizer"],
        "cuisine": "French"
    }).json()
    
    r2 = sqlite_client.post("/api/recipes", json={
        "title": "Onion Rings",
        "description": "Crispy onion rings",
        "ingredients": ["onion", "batter"],
        "instructions": ["Batter onions", "Deep fry"],
        "tags": ["snack"],
        "cuisine": "American"
    }).json()
    
    # Search for Garlic
    response = sqlite_client.get("/api/recipes/search?q=Garlic")
    assert response.status_code == 200
    results = response.json()
    
    # Filter to internal source
    internal = [r for r in results if r.get("source") == "internal"]
    assert len(internal) == 1
    assert internal[0]["title"] == "Garlic Bread"

def test_api_sqlite_update(sqlite_client):
    # Create recipe
    r = sqlite_client.post("/api/recipes", json={
        "title": "Original Pie",
        "description": "Fruit pie",
        "ingredients": ["berries"],
        "instructions": ["bake"],
        "tags": ["dessert"],
        "cuisine": "Global"
    }).json()
    
    # Update recipe
    update_data = {
        "title": "Updated Berry Pie",
        "description": "Delicious fruit pie",
        "ingredients": ["mixed berries", "sugar"],
        "instructions": ["bake at 180C"],
        "tags": ["sweet", "dessert"],
        "cuisine": "Global"
    }
    
    response = sqlite_client.put(f"/api/recipes/{r['id']}", json=update_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated Berry Pie"
    assert updated["ingredients"] == ["mixed berries", "sugar"]
    
    # Get to check
    get_res = sqlite_client.get(f"/api/recipes/{r['id']}")
    assert get_res.json()["title"] == "Updated Berry Pie"

def test_api_sqlite_delete(sqlite_client):
    r = sqlite_client.post("/api/recipes", json={
        "title": "Temporary Soup",
        "description": "Hot soup",
        "ingredients": ["broth"],
        "instructions": ["heat"],
        "tags": ["soup"],
        "cuisine": "Global"
    }).json()
    
    # Delete
    response = sqlite_client.delete(f"/api/recipes/{r['id']}")
    assert response.status_code == 200
    
    # Verify 404
    get_response = sqlite_client.get(f"/api/recipes/{r['id']}")
    assert get_response.status_code == 404
