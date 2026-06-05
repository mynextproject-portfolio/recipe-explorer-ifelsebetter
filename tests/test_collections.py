"""
Tests for Collections and Favorites functionality.
"""

import pytest
from app.models import User, RecipeCreate
from app.dependencies import get_current_user
from app.main import app


def test_collections_crud(client, test_storage):
    """Test creation, listing, details retrieval, and deletion of collections."""
    # Ensure test storage is clean
    test_storage.collections.clear()

    # 1. Create a collection
    col_payload = {"name": "Desserts", "description": "Sweet treats"}
    response = client.post("https://testserver/api/collections", json=col_payload)
    assert response.status_code == 201
    col_data = response.json()
    assert col_data["name"] == "Desserts"
    assert col_data["description"] == "Sweet treats"
    col_id = col_data["id"]

    # 2. List collections
    list_response = client.get("https://testserver/api/collections")
    assert list_response.status_code == 200
    collections = list_response.json()
    assert len(collections) == 1
    assert collections[0]["name"] == "Desserts"

    # 3. Add a recipe to collection
    # First, create a recipe in storage
    recipe_data = RecipeCreate(
        title="Chocolate Cake",
        description="Yummy",
        ingredients=["chocolate", "flour"],
        instructions=["Mix", "Bake"],
        tags=["sweet"],
        cuisine="American"
    )
    recipe = test_storage.create_recipe(recipe_data)
    
    add_res = client.post(f"https://testserver/api/collections/{col_id}/recipes", json={"recipe_id": recipe.id})
    assert add_res.status_code == 200
    
    # Get collection details
    detail_res = client.get(f"https://testserver/api/collections/{col_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["recipes"]) == 1
    assert detail_data["recipes"][0]["title"] == "Chocolate Cake"

    # 4. Remove recipe from collection
    rem_res = client.delete(f"https://testserver/api/collections/{col_id}/recipes/{recipe.id}")
    assert rem_res.status_code == 200
    
    # Get details again to confirm empty
    detail_res_empty = client.get(f"https://testserver/api/collections/{col_id}")
    assert len(detail_res_empty.json()["recipes"]) == 0

    # 5. Delete collection
    del_res = client.delete(f"https://testserver/api/collections/{col_id}")
    assert del_res.status_code == 200
    
    # List collections should be empty
    list_res_empty = client.get("https://testserver/api/collections")
    assert len(list_res_empty.json()) == 0


def test_collection_ownership_isolation(client, test_storage):
    """Test that a user cannot access another user's collection."""
    # Create a collection owned by user 'other-user'
    col_id = "other-col-123"
    from app.models import Collection
    from datetime import datetime
    test_storage.collections[col_id] = Collection(
        id=col_id,
        user_id="other-user",
        name="Other User's Secret List",
        description="Private",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # Make request as 'test-user-id' (defined in conftest.py mock override)
    response = client.get(f"https://testserver/api/collections/{col_id}")
    assert response.status_code == 403
