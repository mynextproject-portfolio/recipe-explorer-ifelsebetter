"""
Tests for TheMealDB adapter — uses mocked responses, no real API calls.

When testing code that calls external APIs, you don't want every test to
hit the real API (slow, unreliable, rate limits). We use respx to mock
httpx requests and response fixtures for deterministic tests.

See test_mealdb_integration.py for the one test that hits the real API.
"""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.mealdb_adapter import MealDBAdapter


# Load the fixture data
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mealdb_response.json"


@pytest.fixture
def fixture_data():
    """Load the TheMealDB response fixture."""
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def adapter():
    """Create a fresh adapter for testing."""
    return MealDBAdapter(
        base_url="https://www.themealdb.com/api/json/v1/1",
        timeout=5.0,
    )


# ─── Transformation Tests ────────────────────────────────────────────────────


class TestTransformMeal:
    """Test the _transform_meal method that converts TheMealDB → our schema."""

    def test_transform_meal_basic(self, adapter, fixture_data):
        """Verify basic ingredient/instruction parsing from fixture data."""
        raw_meal = fixture_data["meals"][0]
        result = adapter._transform_meal(raw_meal)

        assert result is not None
        assert result["id"] == "mealdb-52771"
        assert result["title"] == "Spicy Arrabiata Penne"
        assert result["cuisine"] == "Italian"
        assert result["source"] == "external"

        # Ingredients: 8 non-empty out of 20 slots
        assert len(result["ingredients"]) == 8
        assert "1 pound penne rigate" in result["ingredients"]
        assert "1/4 cup olive oil" in result["ingredients"]
        assert "spinkling Parmigiano-Reggiano" in result["ingredients"]

        # Instructions: should be split into multiple steps
        assert len(result["instructions"]) >= 3
        assert isinstance(result["instructions"], list)

        # Tags parsed from comma-separated string
        assert "Pasta" in result["tags"]
        assert "Curry" in result["tags"]

    def test_transform_meal_sparse_ingredients(self, adapter):
        """Handle meals with only a few ingredient fields populated."""
        raw = {
            "idMeal": "99999",
            "strMeal": "Simple Toast",
            "strArea": "British",
            "strInstructions": "Put bread in toaster.\r\nWait 2 minutes.\r\nButter the toast.",
            "strIngredient1": "bread",
            "strIngredient2": "butter",
            "strIngredient3": "",
            "strMeasure1": "2 slices",
            "strMeasure2": "1 tablespoon",
            "strMeasure3": "",
            "strTags": None,
            "strMealThumb": "",
        }
        result = adapter._transform_meal(raw)

        assert result is not None
        assert len(result["ingredients"]) == 2
        assert "2 slices bread" in result["ingredients"]
        assert "1 tablespoon butter" in result["ingredients"]

    def test_transform_meal_no_measure(self, adapter):
        """Ingredients without measurements still appear."""
        raw = {
            "idMeal": "88888",
            "strMeal": "Plain Rice",
            "strArea": "Global",
            "strInstructions": "Boil water.\r\nAdd rice.\r\nCook 15 minutes.",
            "strIngredient1": "rice",
            "strIngredient2": "water",
            "strMeasure1": "",
            "strMeasure2": "",
            "strTags": None,
            "strMealThumb": "",
        }
        result = adapter._transform_meal(raw)

        assert result is not None
        assert "rice" in result["ingredients"]
        assert "water" in result["ingredients"]

    def test_transform_meal_empty_instructions(self, adapter):
        """Meals with no instructions are skipped (return None)."""
        raw = {
            "idMeal": "77777",
            "strMeal": "No Instructions Meal",
            "strArea": "Italian",
            "strInstructions": "",
            "strIngredient1": "something",
            "strMeasure1": "1 cup",
            "strTags": None,
            "strMealThumb": "",
        }
        result = adapter._transform_meal(raw)
        assert result is None

    def test_transform_meal_numbered_steps(self, adapter):
        """Instructions with numbered steps are parsed correctly."""
        raw = {
            "idMeal": "66666",
            "strMeal": "Numbered Recipe",
            "strArea": "French",
            "strInstructions": "1. Preheat oven to 350F.\n2. Mix the flour and sugar.\n3. Bake for 30 minutes.",
            "strIngredient1": "flour",
            "strMeasure1": "2 cups",
            "strTags": None,
            "strMealThumb": "",
        }
        result = adapter._transform_meal(raw)

        assert result is not None
        assert len(result["instructions"]) == 3
        assert "Preheat oven to 350F." in result["instructions"]

    def test_transform_meal_not_a_dict(self, adapter):
        """Non-dict input returns None."""
        assert adapter._transform_meal("not a dict") is None
        assert adapter._transform_meal(None) is None
        assert adapter._transform_meal(42) is None


# ─── Search Tests (Mocked HTTP) ─────────────────────────────────────────────


class TestSearchByName:
    """Test search_by_name with mocked httpx responses."""

    @respx.mock
    @pytest.mark.anyio
    async def test_search_returns_transformed_results(self, adapter, fixture_data):
        """Mocked search returns properly transformed recipes."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        results, cache_hit = await adapter.search_by_name("arrabiata")

        assert len(results) == 1
        assert results[0]["title"] == "Spicy Arrabiata Penne"
        assert results[0]["cuisine"] == "Italian"
        assert len(results[0]["ingredients"]) == 8
        assert cache_hit is False

    @respx.mock
    @pytest.mark.anyio
    async def test_search_no_results(self, adapter):
        """Search with no matches returns empty list."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, json={"meals": None})
        )

        results, cache_hit = await adapter.search_by_name("xyznonexistent")
        assert results == []
        assert cache_hit is False

    @respx.mock
    @pytest.mark.anyio
    async def test_search_network_timeout(self, adapter):
        """Network timeout returns empty list gracefully."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        results, cache_hit = await adapter.search_by_name("chicken")
        assert results == []

    @respx.mock
    @pytest.mark.anyio
    async def test_search_rate_limited(self, adapter):
        """HTTP 429 (rate limit) returns empty list gracefully."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(429, text="Too Many Requests")
        )

        results, cache_hit = await adapter.search_by_name("chicken")
        assert results == []

    @respx.mock
    @pytest.mark.anyio
    async def test_search_invalid_json(self, adapter):
        """Garbage response returns empty list gracefully."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, text="<html>Not JSON</html>")
        )

        results, cache_hit = await adapter.search_by_name("chicken")
        assert results == []

    @respx.mock
    @pytest.mark.anyio
    async def test_search_unexpected_format(self, adapter):
        """Response missing 'meals' key returns empty list."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, json={"error": "something"})
        )

        results, cache_hit = await adapter.search_by_name("chicken")
        assert results == []

    @respx.mock
    @pytest.mark.anyio
    async def test_search_server_error(self, adapter):
        """HTTP 500 returns empty list gracefully."""
        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        results, cache_hit = await adapter.search_by_name("chicken")
        assert results == []

    @pytest.mark.anyio
    async def test_search_empty_query(self, adapter):
        """Empty/whitespace query returns empty list without making API call."""
        results, _ = await adapter.search_by_name("")
        assert results == []

        results, _ = await adapter.search_by_name("   ")
        assert results == []


# ─── Lookup Tests ────────────────────────────────────────────────────────────


class TestGetById:
    """Test get_by_id with mocked responses."""

    @respx.mock
    @pytest.mark.anyio
    async def test_get_by_id_success(self, adapter, fixture_data):
        """Successful lookup returns a single transformed recipe."""
        respx.get("https://www.themealdb.com/api/json/v1/1/lookup.php").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        result = await adapter.get_by_id("52771")
        assert result is not None
        assert result["id"] == "mealdb-52771"
        assert result["title"] == "Spicy Arrabiata Penne"

    @respx.mock
    @pytest.mark.anyio
    async def test_get_by_id_not_found(self, adapter):
        """Lookup for non-existent ID returns None."""
        respx.get("https://www.themealdb.com/api/json/v1/1/lookup.php").mock(
            return_value=httpx.Response(200, json={"meals": None})
        )

        result = await adapter.get_by_id("99999")
        assert result is None

    @respx.mock
    @pytest.mark.anyio
    async def test_get_by_id_timeout(self, adapter):
        """Timeout on lookup returns None."""
        respx.get("https://www.themealdb.com/api/json/v1/1/lookup.php").mock(
            side_effect=httpx.TimeoutException("Timed out")
        )

        result = await adapter.get_by_id("52771")
        assert result is None

    @pytest.mark.anyio
    async def test_get_by_id_empty_id(self, adapter):
        """Empty ID returns None without API call."""
        result = await adapter.get_by_id("")
        assert result is None


# ─── Parse Response Tests ────────────────────────────────────────────────────


class TestParseResponse:
    """Test the _parse_meals_response method."""

    def test_parse_empty_meals(self, adapter):
        """None meals (TheMealDB's 'no results') returns empty list."""
        assert adapter._parse_meals_response({"meals": None}) == []

    def test_parse_not_a_dict(self, adapter):
        """Non-dict response returns empty list."""
        assert adapter._parse_meals_response("not a dict") == []
        assert adapter._parse_meals_response([]) == []

    def test_parse_meals_not_a_list(self, adapter):
        """meals value that's not a list returns empty list."""
        assert adapter._parse_meals_response({"meals": "oops"}) == []

    def test_parse_skips_bad_meals(self, adapter):
        """Individual meal transform failures are skipped."""
        data = {
            "meals": [
                "not a dict",  # This will fail transform
                {  # This will also fail (no instructions)
                    "idMeal": "11111",
                    "strMeal": "Bad Meal",
                    "strArea": "Test",
                    "strInstructions": "",
                },
            ]
        }
        results = adapter._parse_meals_response(data)
        assert results == []  # Both should be skipped


# ─── Cache Behavior Tests ────────────────────────────────────────────────────


class FakeCache:
    """In-memory cache mock that mimics RedisCache interface."""

    def __init__(self):
        self.store = {}
        self.get_calls = []
        self.set_calls = []

    def get(self, key):
        self.get_calls.append(key)
        return self.store.get(key)

    def set(self, key, value, ttl_seconds=None):
        self.set_calls.append((key, value, ttl_seconds))
        self.store[key] = value
        return True

    @property
    def is_available(self):
        return True


class BrokenCache:
    """Simulates a Redis that's down — all operations return None/False."""

    def get(self, key):
        return None

    def set(self, key, value, ttl_seconds=None):
        return False

    @property
    def is_available(self):
        return False


class TestCacheBehavior:
    """Test caching integration in MealDBAdapter."""

    @respx.mock
    @pytest.mark.anyio
    async def test_cache_miss_stores_results(self, fixture_data):
        """On cache miss, API is called and results are stored in cache."""
        cache = FakeCache()
        adapter = MealDBAdapter(cache=cache)

        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        results, cache_hit = await adapter.search_by_name("arrabiata")

        assert cache_hit is False
        assert len(results) == 1
        assert results[0]["title"] == "Spicy Arrabiata Penne"

        # Verify cache was checked then populated
        assert len(cache.get_calls) == 1
        assert len(cache.set_calls) == 1
        assert cache.set_calls[0][0] == "mealdb:search:arrabiata"

    @pytest.mark.anyio
    async def test_cache_hit_skips_api(self, fixture_data):
        """On cache hit, API is NOT called and cached data is returned."""
        cache = FakeCache()
        cached_results = [
            {
                "id": "mealdb-52771",
                "title": "Spicy Arrabiata Penne",
                "source": "external",
            }
        ]
        cache.store["mealdb:search:arrabiata"] = cached_results

        adapter = MealDBAdapter(cache=cache)

        # No respx mock — if it tries to hit the API, it will fail
        results, cache_hit = await adapter.search_by_name("arrabiata")

        assert cache_hit is True
        assert results == cached_results
        assert len(cache.get_calls) == 1
        assert len(cache.set_calls) == 0  # No new writes

    @respx.mock
    @pytest.mark.anyio
    async def test_broken_cache_falls_through_to_api(self, fixture_data):
        """When Redis is down, adapter falls through to the live API."""
        cache = BrokenCache()
        adapter = MealDBAdapter(cache=cache)

        respx.get("https://www.themealdb.com/api/json/v1/1/search.php").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        results, cache_hit = await adapter.search_by_name("arrabiata")

        assert cache_hit is False
        assert len(results) == 1
        assert results[0]["title"] == "Spicy Arrabiata Penne"

    @respx.mock
    @pytest.mark.anyio
    async def test_cache_miss_on_lookup_stores_result(self, fixture_data):
        """get_by_id caches the result on miss."""
        cache = FakeCache()
        adapter = MealDBAdapter(cache=cache)

        respx.get("https://www.themealdb.com/api/json/v1/1/lookup.php").mock(
            return_value=httpx.Response(200, json=fixture_data)
        )

        result = await adapter.get_by_id("52771")

        assert result is not None
        assert result["id"] == "mealdb-52771"
        assert len(cache.set_calls) == 1
        assert cache.set_calls[0][0] == "mealdb:lookup:52771"

    @pytest.mark.anyio
    async def test_cache_hit_on_lookup(self, fixture_data):
        """get_by_id returns cached result on hit."""
        cache = FakeCache()
        cached_recipe = {"id": "mealdb-52771", "title": "Spicy Arrabiata Penne"}
        cache.store["mealdb:lookup:52771"] = cached_recipe

        adapter = MealDBAdapter(cache=cache)

        result = await adapter.get_by_id("52771")

        assert result == cached_recipe
        assert len(cache.set_calls) == 0
