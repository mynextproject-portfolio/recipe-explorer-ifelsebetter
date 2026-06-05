from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import logging
from pydantic import BaseModel
from app.models import (
    RecipeV2, RecipeV2Create, RecipeV2Update, User,
    Nutrition, Difficulty, Relationships
)
from app.services.interfaces import RecipeStorageInterface, MealDBAdapterInterface
from app.dependencies import (
    get_storage, get_mealdb_adapter,
    get_current_user, get_optional_current_user, verify_csrf_token
)
from app.services.metrics import api_version_requests_total

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2")

# Bulk models
class RecipeV2BulkUpdateItem(BaseModel):
    id: str
    recipe: RecipeV2Update

class RecipeV2BulkUpdateRequest(BaseModel):
    updates: List[RecipeV2BulkUpdateItem]

class RecipeV2BulkDeleteRequest(BaseModel):
    ids: List[str]


@router.get("/recipes", response_model=Dict[str, List[RecipeV2]])
def get_recipes_v2(
    q: Optional[str] = None,
    difficulty: Optional[str] = None,
    dietary: Optional[str] = None,
    cuisine: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Retrieve recipes with v2 fields, filtering, and sorting."""
    api_version_requests_total.labels(version="v2", endpoint="get_recipes").inc()
    
    user_id = current_user.id if current_user else None
    
    if q:
        recipes = storage.search_recipes_v2(
            query=q,
            user_id=user_id,
            difficulty=difficulty,
            dietary=dietary,
            cuisine=cuisine,
            sort_by=sort_by,
            sort_order=sort_order
        )
    else:
        recipes = storage.get_all_recipes_v2(
            user_id=user_id,
            difficulty=difficulty,
            dietary=dietary,
            cuisine=cuisine,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
    return {"recipes": recipes}


@router.get("/recipes/search")
async def search_recipes_unified_v2(
    response: Response,
    q: Optional[str] = None,
    difficulty: Optional[str] = None,
    dietary: Optional[str] = None,
    cuisine: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
    adapter: MealDBAdapterInterface = Depends(get_mealdb_adapter),
):
    """Unified search: combines internal V2 recipes + TheMealDB external results in V2 format."""
    api_version_requests_total.labels(version="v2", endpoint="search_recipes").inc()
    
    user_id = current_user.id if current_user else None
    
    # Internal search using V2 filters and sorting
    if q and q.strip():
        internal = storage.search_recipes_v2(
            query=q,
            user_id=user_id,
            difficulty=difficulty,
            dietary=dietary,
            cuisine=cuisine,
            sort_by=sort_by,
            sort_order=sort_order
        )
    else:
        internal = storage.get_all_recipes_v2(
            user_id=user_id,
            difficulty=difficulty,
            dietary=dietary,
            cuisine=cuisine,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
    internal_results = []
    for recipe in internal:
        recipe_dict = recipe.model_dump()
        recipe_dict["source"] = "internal"
        if recipe_dict.get("created_at"):
            recipe_dict["created_at"] = recipe_dict["created_at"].isoformat()
        if recipe_dict.get("updated_at"):
            recipe_dict["updated_at"] = recipe_dict["updated_at"].isoformat()
            
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
        
    # External search
    external_results = []
    if q and q.strip():
        try:
            raw_ext, _ = await adapter.search_by_name(q)
            for r in raw_ext:
                rid = r.get("id")
                tags = r.get("tags", [])
                dietary_restrictions = []
                tags_lower = [t.lower() for t in tags]
                if "vegan" in tags_lower:
                    dietary_restrictions.append("vegan")
                if "vegetarian" in tags_lower:
                    dietary_restrictions.append("vegetarian")
                
                # Check filter matching for external (gracefully using default metadata)
                if difficulty and difficulty != "medium":
                    continue
                if dietary and dietary not in dietary_restrictions:
                    continue
                if cuisine and r.get("cuisine", "").lower() != cuisine.lower():
                    continue
                
                r_v2 = {
                    "id": rid,
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "ingredients": r.get("ingredients", []),
                    "instructions": r.get("instructions", []),
                    "tags": tags,
                    "cuisine": r.get("cuisine", "Global"),
                    "owner_id": None,
                    "created_at": r.get("created_at"),
                    "updated_at": r.get("updated_at"),
                    "source": "external",
                    "nutrition": {
                        "calories": 250.0,
                        "protein_g": 10.0,
                        "fat_g": 8.0,
                        "carbs_g": 30.0
                    },
                    "dietary_restrictions": dietary_restrictions,
                    "difficulty": {
                        "level": "medium",
                        "prep_time_minutes": 15,
                        "cook_time_minutes": 30
                    },
                    "equipment": [],
                    "techniques": [],
                    "relationships": {
                        "substitutions": {},
                        "variations": []
                    }
                }
                
                if user_id and rid:
                    r_v2["is_favorite"] = storage.is_favorite(user_id, rid)
                    r_v2["user_rating"] = storage.get_user_rating(user_id, rid)
                else:
                    r_v2["is_favorite"] = False
                    r_v2["user_rating"] = None
                    
                stats = storage.get_recipe_rating_stats(rid) if rid else {"average": 0, "count": 0}
                r_v2["average_rating"] = stats["average"]
                r_v2["rating_count"] = stats["count"]
                
                external_results.append(r_v2)
        except Exception as exc:
            logger.warning("V2 External search failed: %s", exc)
            
    all_results = internal_results + external_results
    
    # Sort sorting of the merged list
    if sort_by:
        def get_sort_key(recipe):
            if sort_by == "title":
                return recipe.get("title", "").lower()
            elif sort_by == "created_at":
                return recipe.get("created_at") or ""
            elif sort_by == "updated_at":
                return recipe.get("updated_at") or ""
            elif sort_by == "prep_time":
                return recipe.get("difficulty", {}).get("prep_time_minutes") or 0
            elif sort_by == "cook_time":
                return recipe.get("difficulty", {}).get("cook_time_minutes") or 0
            elif sort_by == "calories":
                return recipe.get("nutrition", {}).get("calories") or 0.0
            return recipe.get("created_at") or ""
        
        reverse = (sort_order and sort_order.lower() == "desc")
        all_results.sort(key=get_sort_key, reverse=reverse)
        
    return all_results


@router.post("/recipes", status_code=201, dependencies=[Depends(verify_csrf_token)])
def create_recipe_v2(
    recipe: RecipeV2Create,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Create a new recipe with v2 properties."""
    api_version_requests_total.labels(version="v2", endpoint="create_recipe").inc()
    return storage.create_recipe_v2(recipe, owner_id=current_user.id)


# --- Bulk Operations (defined BEFORE parameterized paths to prevent collisions) ---

@router.post("/recipes/bulk", status_code=201, dependencies=[Depends(verify_csrf_token)])
def create_recipes_bulk(
    recipes: List[RecipeV2Create],
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Bulk create multiple v2 recipes."""
    api_version_requests_total.labels(version="v2", endpoint="bulk_create_recipes").inc()
    created = storage.create_recipes_bulk(recipes, owner_id=current_user.id)
    return {"message": f"Successfully created {len(created)} recipes", "recipes": created}


@router.put("/recipes/bulk", dependencies=[Depends(verify_csrf_token)])
def update_recipes_bulk(
    payload: RecipeV2BulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Bulk update multiple v2 recipes. Validates ownership of all IDs atomically."""
    api_version_requests_total.labels(version="v2", endpoint="bulk_update_recipes").inc()
    
    updates_list = []
    for item in payload.updates:
        existing = storage.get_recipe_v2(item.id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Recipe with ID {item.id} not found")
        if existing.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own all target recipes")
        updates_list.append((item.id, item.recipe))
        
    updated = storage.update_recipes_bulk(updates_list)
    return {"message": f"Successfully updated {len(updated)} recipes", "recipes": updated}


@router.delete("/recipes/bulk", dependencies=[Depends(verify_csrf_token)])
def delete_recipes_bulk(
    payload: RecipeV2BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Bulk delete multiple recipes. Validates ownership of all IDs atomically."""
    api_version_requests_total.labels(version="v2", endpoint="bulk_delete_recipes").inc()
    
    for rid in payload.ids:
        existing = storage.get_recipe_v2(rid)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Recipe with ID {rid} not found")
        if existing.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own all target recipes")
            
    deleted_count = storage.delete_recipes_bulk(payload.ids)
    return {"message": f"Successfully deleted {deleted_count} recipes", "count": deleted_count}


@router.get("/migration")
def get_migration_details():
    """Returns documentation and details for clients migrating to V2."""
    api_version_requests_total.labels(version="v2", endpoint="migration_guide").inc()
    return {
        "version": "v2",
        "deprecation_timeline": {
            "status": "deprecated",
            "sunset_date": "2026-12-31T23:59:59Z",
            "link": "/api/v2/migration"
        },
        "schema_changes": {
            "nutrition": {
                "type": "object",
                "properties": {
                    "calories": "number",
                    "protein_g": "number",
                    "fat_g": "number",
                    "carbs_g": "number"
                },
                "required": ["calories", "protein_g", "fat_g", "carbs_g"]
            },
            "dietary_restrictions": {
                "type": "array",
                "items": "string"
            },
            "difficulty": {
                "type": "object",
                "properties": {
                    "level": "string",
                    "prep_time_minutes": "integer",
                    "cook_time_minutes": "integer"
                },
                "required": ["level", "prep_time_minutes", "cook_time_minutes"]
            },
            "equipment": {
                "type": "array",
                "items": "string"
            },
            "techniques": {
                "type": "array",
                "items": "string"
            },
            "relationships": {
                "type": "object",
                "properties": {
                    "substitutions": "object",
                    "variations": "array"
                }
            }
        },
        "bulk_endpoints": [
            {"method": "POST", "path": "/api/v2/recipes/bulk", "description": "Bulk create v2 recipes"},
            {"method": "PUT", "path": "/api/v2/recipes/bulk", "description": "Bulk update v2 recipes"},
            {"method": "DELETE", "path": "/api/v2/recipes/bulk", "description": "Bulk delete recipes"}
        ]
    }


# --- Parameterized Paths ---

@router.get("/recipes/{recipe_id}")
def get_recipe_v2_by_id(
    recipe_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Retrieve a specific recipe by ID with V2 attributes and metadata."""
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


@router.put("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def update_recipe_v2_by_id(
    recipe_id: str,
    recipe: RecipeV2Update,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Update a specific v2 recipe by ID."""
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


@router.delete("/recipes/{recipe_id}", dependencies=[Depends(verify_csrf_token)])
def delete_recipe_v2_by_id(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage),
):
    """Delete a specific v2 recipe by ID."""
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
