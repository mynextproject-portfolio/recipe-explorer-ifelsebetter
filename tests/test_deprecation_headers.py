import pytest

def test_v1_endpoints_have_deprecation_headers(client, clean_storage, sample_recipe_data):
    # Create a recipe first
    create_res = client.post("/api/recipes", json=sample_recipe_data)
    assert create_res.status_code == 201
    recipe_id = create_res.json()["id"]

    # Test GET /api/recipes (default V1)
    res = client.get("/api/recipes")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"
    assert "Sunset" in res.headers
    assert "Link" in res.headers

    # Test GET /api/v1/recipes
    res = client.get("/api/v1/recipes")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"

    # Test GET /api/recipes/{id} (default V1)
    res = client.get(f"/api/recipes/{recipe_id}")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"

    # Test GET /api/v1/recipes/{id}
    res = client.get(f"/api/v1/recipes/{recipe_id}")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"

    # Test GET /api/recipes/search (default V1)
    res = client.get("/api/recipes/search?q=Test")
    assert res.status_code == 200
    assert res.headers.get("Deprecation") == "true"


def test_v2_endpoints_do_not_have_deprecation_headers(client, clean_storage, sample_recipe_data):
    # Create a recipe
    create_res = client.post("/api/recipes", json=sample_recipe_data)
    assert create_res.status_code == 201
    recipe_id = create_res.json()["id"]

    # Test GET /api/v2/recipes
    res = client.get("/api/v2/recipes")
    assert res.status_code == 200
    assert "Deprecation" not in res.headers

    # Test GET /api/recipes with Accept: application/vnd.recipe.v2+json
    res = client.get("/api/recipes", headers={"Accept": "application/vnd.recipe.v2+json"})
    assert res.status_code == 200
    assert "Deprecation" not in res.headers

    # Test GET /api/v2/recipes/{id}
    res = client.get(f"/api/v2/recipes/{recipe_id}")
    assert res.status_code == 200
    assert "Deprecation" not in res.headers

    # Test GET /api/recipes/{id} with Accept: application/vnd.recipe.v2+json
    res = client.get(f"/api/recipes/{recipe_id}", headers={"Accept": "application/vnd.recipe.v2+json"})
    assert res.status_code == 200
    assert "Deprecation" not in res.headers
