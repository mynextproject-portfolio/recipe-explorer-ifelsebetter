"""
Interaction routes for Recipe Explorer.

Handles user favorites and recipe ratings.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from app.models import User, Recipe
from app.services.interfaces import RecipeStorageInterface
from app.dependencies import get_storage, get_current_user, get_optional_current_user, verify_csrf_token

router = APIRouter(
    prefix="/api",
    tags=["Interactions"],
    dependencies=[Depends(verify_csrf_token)]
)


class RateRecipePayload(BaseModel):
    rating: int = Field(..., ge=1, le=5)


@router.get("/favorites", response_model=List[Recipe])
def get_favorites(
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Retrieve all recipes favorited by the current user."""
    return storage.get_favorites(current_user.id)


@router.post("/favorites/{recipe_id}")
def add_favorite(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Add a recipe to favorites."""
    # Verify recipe exists locally
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found in local database")
        
    success = storage.add_favorite(current_user.id, recipe_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add to favorites")
        
    return {"message": "Recipe added to favorites", "status": "success"}


@router.delete("/favorites/{recipe_id}")
def remove_favorite(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Remove a recipe from favorites."""
    success = storage.remove_favorite(current_user.id, recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
        
    return {"message": "Recipe removed from favorites", "status": "success"}


@router.get("/recipes/{recipe_id}/rating")
def get_rating_stats(
    recipe_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Get the average rating and user's rating for a specific recipe."""
    stats = storage.get_recipe_rating_stats(recipe_id)
    user_rating = None
    if current_user:
        user_rating = storage.get_user_rating(current_user.id, recipe_id)
    return {
        "average": stats["average"],
        "count": stats["count"],
        "user_rating": user_rating
    }


@router.post("/recipes/{recipe_id}/rate")
def rate_recipe(
    recipe_id: str,
    payload: RateRecipePayload,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Rate a recipe (1-5 stars)."""
    # Verify recipe exists locally
    recipe = storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found in local database")
        
    success = storage.rate_recipe(current_user.id, recipe_id, payload.rating)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit rating")
        
    # Get updated stats
    stats = storage.get_recipe_rating_stats(recipe_id)
    return {
        "message": "Rating submitted successfully",
        "average": stats["average"],
        "count": stats["count"],
        "user_rating": payload.rating
    }
