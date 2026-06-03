from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import logging
from app.models import RecipeCreate, RecipeUpdate
from app.services.storage import recipe_storage

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, search: Optional[str] = None, message: Optional[str] = None):
    """Home page with recipe list and search (internal + external)"""
    if search:
        recipes = recipe_storage.search_recipes(search)
    else:
        recipes = recipe_storage.get_all_recipes()

    # Fetch external results when searching (graceful fallback)
    external_recipes = []
    if search and search.strip():
        try:
            from app.routes.mealdb_routes import get_adapter
            adapter = get_adapter()
            external_recipes = await adapter.search_by_name(search)
        except Exception as exc:
            logger.warning("External search failed on home page: %s", exc)

    return templates.TemplateResponse(request, "index.html", {
        "recipes": recipes,
        "external_recipes": external_recipes,
        "search_query": search or "",
        "message": message
    })


@router.get("/recipes/new", response_class=HTMLResponse)
def new_recipe_form(request: Request):
    """New recipe form"""
    return templates.TemplateResponse(request, "recipe_form.html", {
        "recipe": None,
        "is_edit": False
    })


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(request: Request, recipe_id: str, message: Optional[str] = None):
    """Recipe detail page"""
    recipe = recipe_storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return templates.TemplateResponse(request, "recipe_detail.html", {
        "recipe": recipe,
        "message": message
    })


@router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def edit_recipe_form(request: Request, recipe_id: str):
    """Edit recipe form"""
    recipe = recipe_storage.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return templates.TemplateResponse(request, "recipe_form.html", {
        "recipe": recipe,
        "is_edit": True
    })


@router.post("/recipes/new")
def create_recipe_form(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    cuisine: str = Form(...),
    ingredients: str = Form(...),
    instructions: str = Form(...),
    tags: str = Form(...)
):
    """Handle new recipe form submission"""
    try:
        # Check title length
        if len(title) > 200:
            raise ValueError("Title too long")
        
        # Parse ingredients and instructions (one per line) and tags (comma-separated)
        ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
        instruction_list = [inst.strip() for inst in instructions.split('\n') if inst.strip()]
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # Validation
        if len(ingredient_list) == 0:
            raise ValueError("At least one ingredient required")
        
        if len(instruction_list) == 0:
            raise ValueError("Instructions are required")
        
        recipe_data = RecipeCreate(
            title=title,
            description=description,
            cuisine=cuisine,
            ingredients=ingredient_list,
            instructions=instruction_list,
            tags=tag_list
        )
        
        new_recipe = recipe_storage.create_recipe(recipe_data)
        return RedirectResponse(
            url=f"/recipes/{new_recipe.id}?message=Recipe created successfully",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/?message=Error creating recipe: {str(e)}",
            status_code=303
        )


@router.post("/recipes/{recipe_id}/edit")
def update_recipe_form(
    request: Request,
    recipe_id: str,
    title: str = Form(...),
    description: str = Form(...),
    cuisine: str = Form(...),
    ingredients: str = Form(...),
    instructions: str = Form(...),
    tags: str = Form(...)
):
    """Handle edit recipe form submission"""
    try:
        # Check title length
        if len(title) > 200:
            raise ValueError("Title is too long!")
        
        # Parse ingredients and instructions (one per line) and tags (comma-separated)
        ingredient_list = [ing.strip() for ing in ingredients.split('\n') if ing.strip()]
        instruction_list = [inst.strip() for inst in instructions.split('\n') if inst.strip()]
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        if len(ingredient_list) == 0:
            raise ValueError("Need ingredients!")
            
        if len(instruction_list) == 0:
            raise ValueError("Instructions are required")
        
        recipe_data = RecipeUpdate(
            title=title,
            description=description,
            cuisine=cuisine,
            ingredients=ingredient_list,
            instructions=instruction_list,
            tags=tag_list
        )
        
        updated_recipe = recipe_storage.update_recipe(recipe_id, recipe_data)
        if not updated_recipe:
            return RedirectResponse(
                url=f"/?message=Recipe not found",
                status_code=303
            )
        
        return RedirectResponse(
            url=f"/recipes/{recipe_id}?message=Recipe updated successfully",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/recipes/{recipe_id}?message=Error updating recipe: {str(e)}",
            status_code=303
        )


@router.post("/recipes/{recipe_id}/delete")
def delete_recipe_form(recipe_id: str):
    """Handle recipe deletion"""
    success = recipe_storage.delete_recipe(recipe_id)
    if success:
        return RedirectResponse(
            url="/?message=Recipe deleted successfully",
            status_code=303
        )
    else:
        return RedirectResponse(
            url="/?message=Recipe not found",
            status_code=303
        )


@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request, message: Optional[str] = None):
    """Import recipes page"""
    return templates.TemplateResponse(request, "import.html", {
        "message": message
    })
