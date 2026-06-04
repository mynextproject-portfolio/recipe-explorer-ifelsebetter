"""
External recipe routes — TheMealDB integration endpoints.

Provides search, lookup, save, and combined search endpoints
for fetching recipes from TheMealDB external API.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models import RecipeCreate
from app.services.mealdb_adapter import MealDBAdapter
from app.services.storage import recipe_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recipes")

# Module-level adapter instance, initialized during app lifespan
_adapter: Optional[MealDBAdapter] = None


def get_adapter() -> MealDBAdapter:
    """Get the MealDB adapter, creating a default one if not initialized."""
    global _adapter
    if _adapter is None:
        _adapter = MealDBAdapter()
    return _adapter


def set_adapter(adapter: MealDBAdapter) -> None:
    """Set the MealDB adapter (used during app startup and testing)."""
    global _adapter
    _adapter = adapter


@router.get("/external/search")
async def search_external(q: Optional[str] = None):
    """
    Search TheMealDB for recipes matching a query.

    Returns transformed results in our schema format.
    If TheMealDB is unreachable, returns an empty list with a warning.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    adapter = get_adapter()
    results, _cache_hit = await adapter.search_by_name(q)

    return {
        "source": "external",
        "query": q,
        "count": len(results),
        "recipes": results,
    }


@router.get("/external/{meal_id}")
async def get_external_recipe(meal_id: str):
    """
    Look up a specific recipe from TheMealDB by meal ID.
    """
    adapter = get_adapter()
    recipe = await adapter.get_by_id(meal_id)

    if not recipe:
        raise HTTPException(
            status_code=404, detail=f"Meal '{meal_id}' not found on TheMealDB."
        )

    return recipe


@router.post("/external/{meal_id}/save", status_code=201)
async def save_external_recipe(meal_id: str):
    """
    Fetch a recipe from TheMealDB and save it to internal storage.

    This allows users to "save to collection" — an explicit action
    rather than auto-saving all external results.
    """
    adapter = get_adapter()
    external_recipe = await adapter.get_by_id(meal_id)

    if not external_recipe:
        raise HTTPException(
            status_code=404, detail=f"Meal '{meal_id}' not found on TheMealDB."
        )

    # Check if already saved (by the mealdb-prefixed id)
    existing = recipe_storage.get_recipe(external_recipe["id"])
    if existing:
        return {
            "message": "Recipe already saved",
            "recipe": existing.model_dump(),
        }

    # Create via RecipeCreate (will generate a new internal ID)
    recipe_data = RecipeCreate(
        title=external_recipe["title"],
        description=external_recipe.get("description", ""),
        ingredients=external_recipe.get("ingredients", []),
        instructions=external_recipe["instructions"],
        tags=external_recipe.get("tags", []),
        cuisine=external_recipe["cuisine"],
    )

    saved = recipe_storage.create_recipe(recipe_data)
    logger.info(
        "Saved TheMealDB recipe '%s' as internal recipe '%s'", meal_id, saved.id
    )

    return {
        "message": "Recipe saved to collection",
        "recipe": saved.model_dump(),
    }


@router.get("/search-all")
async def search_all(q: Optional[str] = None):
    """
    Combined search: internal recipes + TheMealDB.

    If TheMealDB is unavailable, still returns internal results.
    This is the graceful degradation endpoint.
    """
    # Internal search
    if q and q.strip():
        internal = recipe_storage.search_recipes(q)
    else:
        internal = recipe_storage.get_all_recipes()

    internal_results = [r.model_dump() for r in internal]

    # External search (with graceful fallback)
    external_results = []
    external_error = None
    if q and q.strip():
        try:
            adapter = get_adapter()
            external_results, _cache_hit = await adapter.search_by_name(q)
        except Exception as exc:
            logger.warning("External search failed, returning internal only: %s", exc)
            external_error = "External API unavailable"

    return {
        "query": q,
        "internal": {
            "count": len(internal_results),
            "recipes": internal_results,
        },
        "external": {
            "source": "external",
            "count": len(external_results),
            "recipes": external_results,
            "error": external_error,
        },
    }
