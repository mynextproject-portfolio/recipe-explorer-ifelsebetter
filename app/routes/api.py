from fastapi import APIRouter, HTTPException, UploadFile, File, Response, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
import json
import logging
import time
from app.models import RecipeCreate, RecipeUpdate, User
from app.services.interfaces import RecipeStorageInterface, MealDBAdapterInterface
from app.dependencies import (
    get_storage, get_mealdb_adapter,
    get_current_user, get_optional_current_user, verify_csrf_token
)
from app.services.metrics import recipe_search_total, recipe_search_terms_total

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/recipes/search")
async def search_recipes_unified(
    response: Response,
    q: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
    adapter: MealDBAdapterInterface = Depends(get_mealdb_adapter),
):
    """
    Unified search: combines internal recipes + TheMealDB external results.

    Each recipe includes a 'source' field ('internal' or 'external').
    If TheMealDB is unavailable, returns only internal results gracefully.
    """
    t_start = time.perf_counter()

    # Get user ID if logged in
    user_id = current_user.id if current_user else None

    # Internal search
    t0 = time.perf_counter()
    if q and q.strip():
        internal = storage.search_recipes(q, user_id=user_id)
    else:
        internal = storage.get_all_recipes(user_id=user_id)

    # Add source and user-specific details (is_favorite, ratings)
    internal_results = []
    for recipe in internal:
        recipe_dict = recipe.model_dump()
        recipe_dict["source"] = "internal"
        # Convert datetime fields to ISO string for consistent JSON
        if "created_at" in recipe_dict and recipe_dict["created_at"]:
            recipe_dict["created_at"] = recipe_dict["created_at"].isoformat()
        if "updated_at" in recipe_dict and recipe_dict["updated_at"]:
            recipe_dict["updated_at"] = recipe_dict["updated_at"].isoformat()
        
        # Inject favorites and ratings data
        if user_id:
            recipe_dict["is_favorite"] = storage.is_favorite(user_id, recipe.id)
            recipe_dict["user_rating"] = storage.get_user_rating(user_id, recipe.id)
        else:
            recipe_dict["is_favorite"] = False
            recipe_dict["user_rating"] = None
            
        stats = storage.get_recipe_rating_stats(recipe.id)
        recipe_dict["average_rating"] = stats["average"]
        recipe_dict["rating_count"] = stats["count"]
        
        internal_results.append(recipe_dict)
    internal_ms = (time.perf_counter() - t0) * 1000.0

    # External search (with graceful fallback)
    external_results = []
    cache_hit = False
    t0 = time.perf_counter()
    if q and q.strip():
        try:
            external_results, cache_hit = await adapter.search_by_name(q)
            # Add dynamic flags to external results
            for r in external_results:
                rid = r.get("id")
                if user_id and rid:
                    r["is_favorite"] = storage.is_favorite(user_id, rid)
                    r["user_rating"] = storage.get_user_rating(user_id, rid)
                else:
                    r["is_favorite"] = False
                    r["user_rating"] = None
                
                stats = storage.get_recipe_rating_stats(rid) if rid else {"average": 0, "count": 0}
                r["average_rating"] = stats["average"]
                r["rating_count"] = stats["count"]
        except Exception as exc:
            logger.warning("External search failed, returning internal only: %s", exc)
    external_ms = (time.perf_counter() - t0) * 1000.0

    # Combine both result sets — internal first, then external
    all_results = internal_results + external_results

    # --- Prometheus metrics ---
    recipe_search_total.labels(source="internal").inc()
    if external_results:
        recipe_search_total.labels(source="external").inc()
    if q and q.strip():
        recipe_search_terms_total.labels(term=q.strip().lower()).inc()

    total_ms = (time.perf_counter() - t_start) * 1000.0

    # Set response headers for performance tracking
    response.headers["X-Internal-Time-Ms"] = f"{internal_ms:.2f}"
    response.headers["X-External-Time-Ms"] = f"{external_ms:.2f}"
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    response.headers["Server-Timing"] = (
        f'internal;dur={internal_ms:.2f};desc="Internal Lookup", '
        f'external;dur={external_ms:.2f};desc="TheMealDB API", '
        f'total;dur={total_ms:.2f};desc="Total Request Time"'
    )

    return all_results


@router.get("/recipes")
def get_recipes(
    search: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get all recipes or search by title"""
    user_id = current_user.id if current_user else None
    if search:
        recipes = storage.search_recipes(search, user_id=user_id)
    else:
        recipes = storage.get_all_recipes(user_id=user_id)

    # Log for debugging (remove in production)
    print(f"Returning {len(recipes)} recipes")

    return {"recipes": recipes}


@router.get("/recipes/internal/{recipe_id}")
def get_internal_recipe(
    recipe_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get a specific internal recipe by ID, tagged with source='internal'."""
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    user_id = current_user.id if current_user else None
    
    recipe_dict = recipe.model_dump()
    recipe_dict["source"] = "internal"
    if recipe_dict.get("created_at"):
        recipe_dict["created_at"] = recipe_dict["created_at"].isoformat()
    if recipe_dict.get("updated_at"):
        recipe_dict["updated_at"] = recipe_dict["updated_at"].isoformat()
        
    # Inject user details
    if user_id:
        recipe_dict["is_favorite"] = storage.is_favorite(user_id, recipe_id)
        recipe_dict["user_rating"] = storage.get_user_rating(user_id, recipe_id)
    else:
        recipe_dict["is_favorite"] = False
        recipe_dict["user_rating"] = None
        
    stats = storage.get_recipe_rating_stats(recipe_id)
    recipe_dict["average_rating"] = stats["average"]
    recipe_dict["rating_count"] = stats["count"]
    
    return recipe_dict


@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: str,
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get a specific recipe by ID"""
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("/recipes", status_code=201, dependencies=[Depends(verify_csrf_token)])
def create_recipe(
    recipe: RecipeCreate,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Create a new recipe"""
    new_recipe = storage.create_recipe(recipe, owner_id=current_user.id)
    return new_recipe


@router.put("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def update_recipe(
    recipe_id: str,
    recipe: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Update an existing recipe"""
    existing = storage.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Enforce ownership check
    if existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this recipe")

    updated_recipe = storage.update_recipe(recipe_id, recipe)
    if not updated_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return updated_recipe


@router.delete("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def delete_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Delete a recipe"""
    existing = storage.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Enforce ownership check
    if existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this recipe")

    success = storage.delete_recipe(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully", "status": "success"}


@router.post("/recipes/import", dependencies=[Depends(verify_csrf_token)])
async def import_recipes(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Import recipes from JSON file"""
    try:
        # Read file
        content = await file.read()

        # Check file size
        if len(content) > 1000000:  # 1MB limit
          return {"error": "File too large"}

        # Parse JSON
        recipes_data = json.loads(content)

        # Validate it's a list
        if not isinstance(recipes_data, list):
            raise HTTPException(
                status_code=400, detail="JSON must be an array of recipes"
            )

        # Log the import (should use proper logging)
        logger.info("Importing %d recipes from %s for user %s", len(recipes_data), file.filename, current_user.username)

        # Inject owner_id into imported recipes if they don't have it
        for r_data in recipes_data:
            if "owner_id" not in r_data or not r_data["owner_id"]:
                r_data["owner_id"] = current_user.id

        # Actually import
        count = storage.import_recipes(recipes_data)

        return {"message": f"Successfully imported {count} recipes", "count": count}

    except json.JSONDecodeError as e:
        logger.warning("JSON error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except ValueError as e:
        # Schema validation error from storage
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/recipes/export")
def export_recipes(
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Export all recipes belonging to the current user as JSON"""
    recipes = storage.get_all_recipes(user_id=current_user.id)
    # Filter to user's own recipes only, or include public ones?
    # Export user's private recipes
    user_recipes = [r for r in recipes if r.owner_id == current_user.id]
    recipes_dict = [recipe.model_dump() for recipe in user_recipes]
    # Format datetime fields to string
    for r in recipes_dict:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("updated_at"):
            r["updated_at"] = r["updated_at"].isoformat()
    return JSONResponse(content=recipes_dict)
