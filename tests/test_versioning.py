import pytest

def test_get_recipes_versioning(client, clean_storage, sample_recipe_data):
    # Create a recipe with V2 data first via explicit V2 endpoint
    v2_recipe = sample_recipe_data.copy()
    v2_recipe.update({
        "nutrition": {"calories": 300, "protein_g": 10, "fat_g": 5, "carbs_g": 20},
        "dietary_restrictions": ["vegan"],
        "difficulty": {"level": "easy", "prep_time_minutes": 5, "cook_time_minutes": 10},
        "equipment": ["pot"],
        "techniques": ["boiling"],
    })
    
    create_res = client.post("/api/v2/recipes", json=v2_recipe)
    assert create_res.status_code == 201
    recipe_id = create_res.json()["id"]

    # 1. GET via standard endpoint without Accept header -> Returns V1 (stripped V2 fields)
    res_v1_no_header = client.get("/api/recipes")
    assert res_v1_no_header.status_code == 200
    recipe_v1 = res_v1_no_header.json()["recipes"][0]
    assert "nutrition" not in recipe_v1
    assert "dietary_restrictions" not in recipe_v1
    assert "difficulty" not in recipe_v1
    assert "equipment" not in recipe_v1
    assert "techniques" not in recipe_v1

    # 2. GET via standard endpoint with Accept: application/json -> Returns V1
    res_v1_json = client.get("/api/recipes", headers={"Accept": "application/json"})
    assert res_v1_json.status_code == 200
    recipe_v1_json = res_v1_json.json()["recipes"][0]
    assert "nutrition" not in recipe_v1_json

    # 3. GET via standard endpoint with Accept: application/vnd.recipe.v2+json -> Returns V2
    res_v2_negotiated = client.get("/api/recipes", headers={"Accept": "application/vnd.recipe.v2+json"})
    assert res_v2_negotiated.status_code == 200
    recipe_v2 = res_v2_negotiated.json()["recipes"][0]
    assert "nutrition" in recipe_v2
    assert recipe_v2["nutrition"]["calories"] == 300
    assert recipe_v2["dietary_restrictions"] == ["vegan"]
    assert recipe_v2["difficulty"]["level"] == "easy"
    assert recipe_v2["equipment"] == ["pot"]
    assert recipe_v2["techniques"] == ["boiling"]

    # 4. GET via explicit /api/v1/recipes prefix -> Returns V1
    res_v1_prefix = client.get("/api/v1/recipes")
    assert res_v1_prefix.status_code == 200
    recipe_v1_prefix = res_v1_prefix.json()["recipes"][0]
    assert "nutrition" not in recipe_v1_prefix

    # 5. GET via explicit /api/v2/recipes prefix -> Returns V2
    res_v2_prefix = client.get("/api/v2/recipes")
    assert res_v2_prefix.status_code == 200
    recipe_v2_prefix = res_v2_prefix.json()["recipes"][0]
    assert "nutrition" in recipe_v2_prefix
    assert recipe_v2_prefix["nutrition"]["calories"] == 300


def test_get_single_recipe_versioning(client, clean_storage, sample_recipe_data):
    v2_recipe = sample_recipe_data.copy()
    v2_recipe.update({
        "nutrition": {"calories": 300, "protein_g": 10, "fat_g": 5, "carbs_g": 20},
    })
    create_res = client.post("/api/v2/recipes", json=v2_recipe)
    recipe_id = create_res.json()["id"]

    # standard V1
    res = client.get(f"/api/recipes/{recipe_id}")
    assert res.status_code == 200
    assert "nutrition" not in res.json()

    # standard V2 negotiated
    res = client.get(f"/api/recipes/{recipe_id}", headers={"Accept": "application/vnd.recipe.v2+json"})
    assert res.status_code == 200
    assert "nutrition" in res.json()
    assert res.json()["nutrition"]["calories"] == 300

    # explicit V1 prefix
    res = client.get(f"/api/v1/recipes/{recipe_id}")
    assert res.status_code == 200
    assert "nutrition" not in res.json()

    # explicit V2 prefix
    res = client.get(f"/api/v2/recipes/{recipe_id}")
    assert res.status_code == 200
    assert "nutrition" in res.json()
