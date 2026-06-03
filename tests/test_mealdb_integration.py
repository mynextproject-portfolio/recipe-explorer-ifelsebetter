"""
Integration test — actually hits the real TheMealDB API.

This is the ONE test that verifies the real API adapter works end-to-end.
It is marked with @pytest.mark.integration so it's skipped by default
and only run explicitly:

    pytest -m integration

Keep at least one integration test to verify the real API adapter works,
but use mocking (test_mealdb_adapter.py) for everything else.
"""
import pytest

from app.services.mealdb_adapter import MealDBAdapter


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_mealdb_search():
    """
    Integration test: search TheMealDB for 'Arrabiata' and verify
    the response transforms correctly into our schema.

    This test hits the real API — it may fail if:
    - TheMealDB is down
    - Network is unavailable
    - TheMealDB changes their response format
    """
    adapter = MealDBAdapter(timeout=10.0)  # Generous timeout for CI

    results = await adapter.search_by_name("Arrabiata")

    # TheMealDB should have at least one Arrabiata recipe
    assert len(results) >= 1

    recipe = results[0]

    # Verify our schema transformation worked
    assert "id" in recipe
    assert recipe["id"].startswith("mealdb-")
    assert "title" in recipe
    assert "Arrabiata" in recipe["title"]
    assert recipe["cuisine"] == "Italian"
    assert recipe["source"] == "mealdb"

    # Verify ingredients were collected from strIngredient1..20
    assert isinstance(recipe["ingredients"], list)
    assert len(recipe["ingredients"]) >= 1

    # Verify instructions were parsed from text block into array
    assert isinstance(recipe["instructions"], list)
    assert len(recipe["instructions"]) >= 1

    # Each instruction should be a non-empty string
    for step in recipe["instructions"]:
        assert isinstance(step, str)
        assert len(step.strip()) > 0

    # Tags should be a list (may be empty)
    assert isinstance(recipe["tags"], list)


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_mealdb_lookup():
    """
    Integration test: look up Arrabiata by its known ID (52771).
    """
    adapter = MealDBAdapter(timeout=10.0)

    result = await adapter.get_by_id("52771")

    assert result is not None
    assert result["id"] == "mealdb-52771"
    assert "Arrabiata" in result["title"]
    assert result["cuisine"] == "Italian"
    assert len(result["ingredients"]) >= 4
    assert len(result["instructions"]) >= 3


@pytest.mark.integration
@pytest.mark.anyio
async def test_real_mealdb_search_no_results():
    """
    Integration test: searching for nonsense returns empty results.
    """
    adapter = MealDBAdapter(timeout=10.0)

    results = await adapter.search_by_name("xyzzy_nonexistent_meal_12345")
    assert results == []
