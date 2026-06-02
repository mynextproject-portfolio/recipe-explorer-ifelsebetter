"""
Comprehensive contract tests for Recipe Explorer API.
These tests verify that endpoints exist, return expected status codes (200, 201, 400, 404, 422),
and return correctly structured data.
"""

def test_health_check(client):
    """Smoke test: API is running and responding"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_home_page_loads(client):
    """Smoke test: Home page renders without error"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Recipe Explorer" in response.text


def test_get_all_recipes(client, clean_storage):
    """Contract test: GET /api/recipes returns correct structure"""
    response = client.get("/api/recipes")
    assert response.status_code == 200
    data = response.json()
    assert "recipes" in data
    assert isinstance(data["recipes"], list)


def test_create_and_get_recipe(client, clean_storage, sample_recipe_data):
    """Contract test: Create recipe and verify response structure"""
    # Create recipe
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    assert create_response.status_code == 201
    
    recipe = create_response.json()
    assert "id" in recipe
    assert "title" in recipe
    assert "created_at" in recipe
    assert recipe["title"] == sample_recipe_data["title"]
    
    # Get recipe
    get_response = client.get(f"/api/recipes/{recipe['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == recipe["id"]


def test_create_recipe_invalid_data(client, clean_storage):
    """Contract test: Invalid recipe data returns 422"""
    invalid_data = {
        "title": "Missing fields recipe"
    }
    response = client.post("/api/recipes", json=invalid_data)
    assert response.status_code == 422


def test_recipe_not_found(client, clean_storage):
    """Contract test: Non-existent recipe returns 404"""
    response = client.get("/api/recipes/non-existent-id")
    assert response.status_code == 404


def test_update_recipe(client, clean_storage, sample_recipe_data):
    """Contract test: Update existing recipe returns 200"""
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    update_data = sample_recipe_data.copy()
    update_data["title"] = "Updated Title"

    response = client.put(f"/api/recipes/{recipe_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_recipe_not_found(client, clean_storage, sample_recipe_data):
    """Contract test: Update non-existent recipe returns 404"""
    response = client.put("/api/recipes/non-existent-id", json=sample_recipe_data)
    assert response.status_code == 404


def test_update_recipe_invalid_data(client, clean_storage, sample_recipe_data):
    """Contract test: Update with invalid schema returns 422"""
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    response = client.put(f"/api/recipes/{recipe_id}", json={"title": "Missing fields"})
    assert response.status_code == 422


def test_delete_recipe(client, clean_storage, sample_recipe_data):
    """Contract test: Delete existing recipe returns 200"""
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]

    response = client.delete(f"/api/recipes/{recipe_id}")
    assert response.status_code == 200

    # Verify it is deleted
    get_response = client.get(f"/api/recipes/{recipe_id}")
    assert get_response.status_code == 404


def test_delete_recipe_not_found(client, clean_storage):
    """Contract test: Delete non-existent recipe returns 404"""
    response = client.delete("/api/recipes/non-existent-id")
    assert response.status_code == 404


def test_import_recipes(client, clean_storage, sample_recipe_data):
    """Contract test: Import valid JSON returns 200"""
    import io
    import json
    
    file_content = json.dumps([sample_recipe_data])
    file_obj = io.BytesIO(file_content.encode('utf-8'))
    
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", file_obj, "application/json")}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_import_recipes_invalid_format(client, clean_storage):
    """Contract test: Import malformed JSON returns 400"""
    import io
    
    file_content = "{ malformed json"
    file_obj = io.BytesIO(file_content.encode('utf-8'))
    
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", file_obj, "application/json")}
    )
    assert response.status_code == 400


def test_import_recipes_invalid_data(client, clean_storage):
    """Contract test: Import JSON with invalid schema returns 422"""
    import io
    import json
    
    # JSON is valid format, but schema is incorrect (missing required fields)
    file_content = json.dumps([{"title": "Missing required fields"}])
    file_obj = io.BytesIO(file_content.encode('utf-8'))
    
    response = client.post(
        "/api/recipes/import",
        files={"file": ("recipes.json", file_obj, "application/json")}
    )
    assert response.status_code == 422


def test_recipe_pages_load(client, clean_storage, sample_recipe_data):
    """Smoke test: Recipe HTML pages load without error"""
    create_response = client.post("/api/recipes", json=sample_recipe_data)
    recipe_id = create_response.json()["id"]
    
    assert client.get(f"/recipes/{recipe_id}").status_code == 200
    assert client.get("/recipes/new").status_code == 200
    assert client.get("/import").status_code == 200
