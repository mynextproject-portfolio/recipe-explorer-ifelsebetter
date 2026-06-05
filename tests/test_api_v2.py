import pytest
from app.dependencies import get_current_user
from app.models import User
from app.main import app

@pytest.fixture
def sample_recipe_v2_data(sample_recipe_data):
    v2_data = sample_recipe_data.copy()
    v2_data.update({
        "nutrition": {
            "calories": 450.0,
            "protein_g": 25.0,
            "fat_g": 15.0,
            "carbs_g": 55.0
        },
        "dietary_restrictions": ["vegetarian", "dairy-free"],
        "difficulty": {
            "level": "medium",
            "prep_time_minutes": 15,
            "cook_time_minutes": 30
        },
        "equipment": ["frying pan", "bowl"],
        "techniques": ["sauteing", "mixing"],
        "relationships": {
            "substitutions": {"milk": "almond milk"},
            "variations": []
        }
    })
    return v2_data


def test_v2_crud_operations(client, clean_storage, sample_recipe_v2_data):
    # 1. Create a V2 Recipe
    create_res = client.post("/api/v2/recipes", json=sample_recipe_v2_data)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["nutrition"]["calories"] == 450.0
    assert created["difficulty"]["level"] == "medium"
    assert "vegetarian" in created["dietary_restrictions"]
    assert created["equipment"] == ["frying pan", "bowl"]
    
    recipe_id = created["id"]
    
    # 2. Get the V2 Recipe by ID
    get_res = client.get(f"/api/v2/recipes/{recipe_id}")
    assert get_res.status_code == 200
    recipe_get = get_res.json()
    assert recipe_get["id"] == recipe_id
    assert recipe_get["nutrition"]["protein_g"] == 25.0
    assert recipe_get["difficulty"]["prep_time_minutes"] == 15
    assert recipe_get["relationships"]["substitutions"] == {"milk": "almond milk"}
    
    # 3. Update the V2 Recipe
    update_payload = sample_recipe_v2_data.copy()
    update_payload["nutrition"]["calories"] = 500.0
    update_payload["difficulty"]["level"] = "hard"
    
    put_res = client.put(f"/api/v2/recipes/{recipe_id}", json=update_payload)
    assert put_res.status_code == 200
    recipe_put = put_res.json()
    assert recipe_put["nutrition"]["calories"] == 500.0
    assert recipe_put["difficulty"]["level"] == "hard"
    
    # 4. Delete the V2 Recipe
    del_res = client.delete(f"/api/v2/recipes/{recipe_id}")
    assert del_res.status_code == 200
    
    # Verify it is deleted
    assert client.get(f"/api/v2/recipes/{recipe_id}").status_code == 404


def test_v2_filtering_and_sorting(client, clean_storage, sample_recipe_v2_data):
    # Seed 3 distinct recipes
    # Recipe 1: easy, vegan, Italian, calories=150, prep=5
    r1 = sample_recipe_v2_data.copy()
    r1.update({
        "title": "A Salad",
        "cuisine": "Italian",
        "nutrition": {"calories": 150.0, "protein_g": 2.0, "fat_g": 5.0, "carbs_g": 10.0},
        "dietary_restrictions": ["vegan", "gluten-free"],
        "difficulty": {"level": "easy", "prep_time_minutes": 5, "cook_time_minutes": 0}
    })
    client.post("/api/v2/recipes", json=r1)

    # Recipe 2: medium, vegetarian, Global, calories=350, prep=15
    r2 = sample_recipe_v2_data.copy()
    r2.update({
        "title": "B Pasta",
        "cuisine": "Global",
        "nutrition": {"calories": 350.0, "protein_g": 12.0, "fat_g": 10.0, "carbs_g": 40.0},
        "dietary_restrictions": ["vegetarian"],
        "difficulty": {"level": "medium", "prep_time_minutes": 15, "cook_time_minutes": 20}
    })
    client.post("/api/v2/recipes", json=r2)

    # Recipe 3: hard, vegan, Mexican, calories=600, prep=30
    r3 = sample_recipe_v2_data.copy()
    r3.update({
        "title": "C Tacos",
        "cuisine": "Mexican",
        "nutrition": {"calories": 600.0, "protein_g": 20.0, "fat_g": 22.0, "carbs_g": 65.0},
        "dietary_restrictions": ["vegan"],
        "difficulty": {"level": "hard", "prep_time_minutes": 30, "cook_time_minutes": 45}
    })
    client.post("/api/v2/recipes", json=r3)

    # Filter by difficulty = easy
    res = client.get("/api/v2/recipes?difficulty=easy")
    assert res.status_code == 200
    recipes = res.json()["recipes"]
    assert len(recipes) == 1
    assert recipes[0]["title"] == "A Salad"

    # Filter by dietary = vegan
    res = client.get("/api/v2/recipes?dietary=vegan")
    assert res.status_code == 200
    recipes = res.json()["recipes"]
    assert len(recipes) == 2
    assert any(x["title"] == "A Salad" for x in recipes)
    assert any(x["title"] == "C Tacos" for x in recipes)

    # Filter by cuisine = Mexican
    res = client.get("/api/v2/recipes?cuisine=Mexican")
    assert res.status_code == 200
    recipes = res.json()["recipes"]
    assert len(recipes) == 1
    assert recipes[0]["title"] == "C Tacos"

    # Sort by calories ascending
    res = client.get("/api/v2/recipes?sort_by=calories&sort_order=asc")
    assert res.status_code == 200
    recipes = res.json()["recipes"]
    assert [x["title"] for x in recipes] == ["A Salad", "B Pasta", "C Tacos"]

    # Sort by prep_time descending
    res = client.get("/api/v2/recipes?sort_by=prep_time&sort_order=desc")
    assert res.status_code == 200
    recipes = res.json()["recipes"]
    assert [x["title"] for x in recipes] == ["C Tacos", "B Pasta", "A Salad"]


def test_v2_unified_search(client, clean_storage, sample_recipe_v2_data):
    # Seed internal recipe
    recipe_data = sample_recipe_v2_data.copy()
    recipe_data["title"] = "V2 internal chicken recipe"
    client.post("/api/v2/recipes", json=recipe_data)

    # Search for chicken - combines internal and external (FakeMealDB returns penne)
    res = client.get("/api/v2/recipes/search?q=chicken")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 2
    
    internal_res = [x for x in results if x.get("source") == "internal"]
    external_res = [x for x in results if x.get("source") == "external"]
    
    assert len(internal_res) == 1
    assert len(external_res) == 1
    assert "nutrition" in external_res[0]
    assert "difficulty" in external_res[0]


def test_v2_bulk_operations(client, clean_storage, sample_recipe_v2_data):
    # 1. Bulk Create
    recipe1 = sample_recipe_v2_data.copy()
    recipe1["title"] = "Bulk 1"
    recipe2 = sample_recipe_v2_data.copy()
    recipe2["title"] = "Bulk 2"
    
    bulk_create_res = client.post("/api/v2/recipes/bulk", json=[recipe1, recipe2])
    assert bulk_create_res.status_code == 201
    created_recipes = bulk_create_res.json()["recipes"]
    assert len(created_recipes) == 2
    
    id1 = created_recipes[0]["id"]
    id2 = created_recipes[1]["id"]
    
    # 2. Bulk Update
    update1 = sample_recipe_v2_data.copy()
    update1["title"] = "Bulk 1 Updated"
    update2 = sample_recipe_v2_data.copy()
    update2["title"] = "Bulk 2 Updated"
    
    bulk_update_res = client.put("/api/v2/recipes/bulk", json={
        "updates": [
            {"id": id1, "recipe": update1},
            {"id": id2, "recipe": update2}
        ]
    })
    assert bulk_update_res.status_code == 200
    updated_recipes = bulk_update_res.json()["recipes"]
    assert len(updated_recipes) == 2
    assert updated_recipes[0]["title"] == "Bulk 1 Updated"
    assert updated_recipes[1]["title"] == "Bulk 2 Updated"
    
    # 3. Bulk Delete
    bulk_del_res = client.request("DELETE", "/api/v2/recipes/bulk", json={
        "ids": [id1, id2]
    })
    assert bulk_del_res.status_code == 200
    assert bulk_del_res.json()["count"] == 2
    
    # Verify both deleted
    assert client.get(f"/api/v2/recipes/{id1}").status_code == 404
    assert client.get(f"/api/v2/recipes/{id2}").status_code == 404


def test_v2_bulk_ownership_check(client, clean_storage, sample_recipe_v2_data):
    # Create a recipe owned by test-user-id
    create_res = client.post("/api/v2/recipes", json=sample_recipe_v2_data)
    recipe_id = create_res.json()["id"]

    # Temporarily override get_current_user dependency to represent a different user
    another_user = User(
        id="another-user-id",
        username="anotheruser",
        email="anotheruser@example.com",
        password_hash="another_hash",
        profile_name="Another User",
        preferences={}
    )
    app.dependency_overrides[get_current_user] = lambda: another_user

    try:
        # Attempting to bulk update a recipe owned by another user must return 403 Forbidden
        update_data = sample_recipe_v2_data.copy()
        update_data["title"] = "Malicious Update"
        
        bulk_update_res = client.put("/api/v2/recipes/bulk", json={
            "updates": [
                {"id": recipe_id, "recipe": update_data}
            ]
        })
        assert bulk_update_res.status_code == 403

        # Attempting to bulk delete a recipe owned by another user must return 403 Forbidden
        bulk_del_res = client.request("DELETE", "/api/v2/recipes/bulk", json={
            "ids": [recipe_id]
        })
        assert bulk_del_res.status_code == 403
    finally:
        # Restore mock user dependency override
        mock_user = User(
            id="test-user-id",
            username="testuser",
            email="testuser@example.com",
            password_hash="mock_hash",
            profile_name="Test User",
            preferences={}
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user
