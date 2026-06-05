from fastapi import APIRouter, HTTPException, UploadFile, File, Response, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
import json
import logging
import time
from app.models import Recipe, RecipeCreate, RecipeUpdate, User, RecipeV2Create, RecipeV2Update
from app.services.interfaces import RecipeStorageInterface, MealDBAdapterInterface
from app.dependencies import (
    get_storage, get_mealdb_adapter,
    get_current_user, get_optional_current_user, verify_csrf_token,
    get_api_version
)
from app.services.metrics import recipe_search_total, recipe_search_terms_total, api_version_requests_total

logger = logging.getLogger(__name__)

# Note: Prefix is removed from APIRouter definition to allow mounting with different prefixes (/api and /api/v1) in main.py
router = APIRouter()


def inject_deprecation_headers(response: Response) -> None:
    """Inject RFC-compliant deprecation and sunset headers for v1 endpoints."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Thu, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '</api/v2/migration>; rel="sunset"'


def strip_v2_fields(recipe_dict: dict) -> dict:
    """Strip all V2 specific fields from a dictionary to guarantee backward compatibility."""
    v2_fields = ["nutrition", "dietary_restrictions", "difficulty", "equipment", "techniques", "relationships"]
    for field in v2_fields:
        recipe_dict.pop(field, None)
    return recipe_dict


@router.get("/recipes/search")
async def search_recipes_unified(
    request: Request,
    response: Response,
    q: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
    adapter: MealDBAdapterInterface = Depends(get_mealdb_adapter),
):
    """
    Unified search: combines internal recipes + TheMealDB external results.
    Performs version negotiation based on Request Accept header or URL path.
    """
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="search_recipes").inc()
        # Delegate to V2 unified search logic
        from app.routes.api_v2 import search_recipes_unified_v2
        return await search_recipes_unified_v2(
            response=response,
            q=q,
            current_user=current_user,
            storage=storage,
            adapter=adapter
        )

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="search_recipes").inc()
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
        recipe_dict = strip_v2_fields(recipe_dict)
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
    request: Request,
    response: Response,
    search: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get all recipes or search by title."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="get_recipes").inc()
        user_id = current_user.id if current_user else None
        if search:
            recipes = storage.search_recipes_v2(search, user_id=user_id)
        else:
            recipes = storage.get_all_recipes_v2(user_id=user_id)
        return {"recipes": recipes}

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="get_recipes").inc()
    user_id = current_user.id if current_user else None
    if search:
        recipes = storage.search_recipes(search, user_id=user_id)
    else:
        recipes = storage.get_all_recipes(user_id=user_id)

    # Strictly strip V2 fields from returned V1 array
    recipes_v1 = [strip_v2_fields(r.model_dump()) for r in recipes]
    return {"recipes": recipes_v1}


@router.get("/recipes/internal/{recipe_id}")
def get_internal_recipe(
    recipe_id: str,
    request: Request,
    response: Response,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get a specific internal recipe by ID."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="get_recipe_by_id").inc()
        recipe = storage.get_recipe_v2(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        user_id = current_user.id if current_user else None
        recipe_dict = recipe.model_dump()
        recipe_dict["source"] = "internal"
        if recipe_dict.get("created_at"):
            recipe_dict["created_at"] = recipe_dict["created_at"].isoformat()
        if recipe_dict.get("updated_at"):
            recipe_dict["updated_at"] = recipe_dict["updated_at"].isoformat()
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

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="get_recipe_by_id").inc()
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
        
    user_id = current_user.id if current_user else None
    
    recipe_dict = recipe.model_dump()
    recipe_dict = strip_v2_fields(recipe_dict)
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
    request: Request,
    response: Response,
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Get a specific recipe by ID."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="get_recipe_raw").inc()
        recipe = storage.get_recipe_v2(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="get_recipe_raw").inc()
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Cast to Recipe model so extra V2 fields are ignored by validation
    return Recipe(**recipe.model_dump())


@router.post("/recipes", status_code=201, dependencies=[Depends(verify_csrf_token)])
def create_recipe(
    request: Request,
    response: Response,
    recipe: RecipeV2Create,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Create a new recipe."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="create_recipe").inc()
        return storage.create_recipe_v2(recipe, owner_id=current_user.id)

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="create_recipe").inc()
    # Strip down to V1 schema
    v1_data = RecipeCreate(**recipe.model_dump(exclude_unset=True))
    created = storage.create_recipe(v1_data, owner_id=current_user.id)
    return Recipe(**created.model_dump())


@router.put("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def update_recipe(
    recipe_id: str,
    request: Request,
    response: Response,
    recipe: RecipeV2Update,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Update an existing recipe."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="update_recipe").inc()
        existing = storage.get_recipe_v2(recipe_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if existing.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this recipe")
        
        updated = storage.update_recipe_v2(recipe_id, recipe)
        if not updated:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return updated

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="update_recipe").inc()
    existing = storage.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this recipe")

    v1_data = RecipeUpdate(**recipe.model_dump(exclude_unset=True))
    updated_recipe = storage.update_recipe(recipe_id, v1_data)
    if not updated_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return Recipe(**updated_recipe.model_dump())


@router.delete("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def delete_recipe(
    recipe_id: str,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Delete a recipe."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="delete_recipe").inc()
        existing = storage.get_recipe_v2(recipe_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if existing.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this recipe")
        success = storage.delete_recipe(recipe_id)
        if not success:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return {"message": "Recipe deleted successfully", "status": "success"}

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="delete_recipe").inc()
    existing = storage.get_recipe(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if existing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this recipe")

    success = storage.delete_recipe(recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully", "status": "success"}


@router.post("/recipes/import", dependencies=[Depends(verify_csrf_token)])
async def import_recipes(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Import recipes from JSON file."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="import_recipes").inc()
    else:
        inject_deprecation_headers(response)
        api_version_requests_total.labels(version="v1", endpoint="import_recipes").inc()

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
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/recipes/export")
def export_recipes(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Export all recipes belonging to the current user as JSON."""
    version = get_api_version(request)
    if version == "v2":
        api_version_requests_total.labels(version="v2", endpoint="export_recipes").inc()
        recipes = storage.get_all_recipes_v2(user_id=current_user.id)
        user_recipes = [r for r in recipes if r.owner_id == current_user.id]
        recipes_dict = [recipe.model_dump() for recipe in user_recipes]
        for r in recipes_dict:
            if r.get("created_at"):
                r["created_at"] = r["created_at"].isoformat()
            if r.get("updated_at"):
                r["updated_at"] = r["updated_at"].isoformat()
        return JSONResponse(content=recipes_dict)

    # V1 Legacy logic
    inject_deprecation_headers(response)
    api_version_requests_total.labels(version="v1", endpoint="export_recipes").inc()
    recipes = storage.get_all_recipes(user_id=current_user.id)
    user_recipes = [r for r in recipes if r.owner_id == current_user.id]
    recipes_dict = [recipe.model_dump() for recipe in user_recipes]
    for r in recipes_dict:
        r = strip_v2_fields(r)
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("updated_at"):
            r["updated_at"] = r["updated_at"].isoformat()
    return JSONResponse(content=recipes_dict)
