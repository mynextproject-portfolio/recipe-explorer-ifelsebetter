"""
Collections routes for Recipe Explorer.

Handles personal collections: creation, listing, deletion,
and adding/removing recipes from a collection.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.models import User, Collection, CollectionCreate, Recipe
from app.services.interfaces import RecipeStorageInterface
from app.dependencies import get_storage, get_current_user, verify_csrf_token

router = APIRouter(
    prefix="/api/collections",
    tags=["Collections"],
    dependencies=[Depends(verify_csrf_token)]
)


class AddRecipePayload(BaseModel):
    recipe_id: str


@router.get("", response_model=List[Collection])
def list_collections(
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """List all collections created by the current user."""
    return storage.get_collections(current_user.id)


@router.post("", response_model=Collection, status_code=201)
def create_collection(
    payload: CollectionCreate,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Create a new personal recipe collection."""
    return storage.create_collection(current_user.id, payload)


@router.get("/{collection_id}")
def get_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Retrieve details and recipes of a specific collection."""
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    # Verify ownership
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    recipes = storage.get_collection_recipes(collection_id)
    
    # Return collection data with its recipes
    return {
        "id": collection.id,
        "user_id": collection.user_id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "recipes": recipes
    }


@router.delete("/{collection_id}")
def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Delete a collection."""
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    # Verify ownership
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    storage.delete_collection(collection_id)
    return {"message": "Collection deleted successfully"}


@router.post("/{collection_id}/recipes")
def add_recipe(
    collection_id: str,
    payload: AddRecipePayload,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Add a recipe to a collection."""
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    # Verify ownership of collection
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    # Verify recipe exists in DB first. (If it doesn't, they need to save it first)
    recipe = storage.get_recipe(payload.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found in local database")
        
    success = storage.add_recipe_to_collection(collection_id, payload.recipe_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add recipe to collection")
        
    return {"message": "Recipe added to collection successfully"}


@router.delete("/{collection_id}/recipes/{recipe_id}")
def remove_recipe(
    collection_id: str,
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    """Remove a recipe from a collection."""
    collection = storage.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    # Verify ownership
    if collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    success = storage.remove_recipe_from_collection(collection_id, recipe_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recipe not found in collection")
        
    return {"message": "Recipe removed from collection successfully"}
