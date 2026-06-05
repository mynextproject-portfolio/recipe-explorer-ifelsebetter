import os
import tempfile
from datetime import datetime
import pytest
from app.models import RecipeCreate, RecipeUpdate
from app.services.sqlite_storage import SQLiteRecipeStorage

@pytest.fixture
def temp_db():
    # Create a temporary file for the SQLite database
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_sqlite_create_and_get(temp_db):
    storage = SQLiteRecipeStorage(db_path=temp_db)
    
    recipe_data = RecipeCreate(
        title="SQLite Test Recipe",
        description="Testing SQLite storage",
        ingredients=["water", "salt"],
        instructions=["Boil water", "Add salt"],
        tags=["test", "sqlite"],
        cuisine="Italian"
    )
    
    created = storage.create_recipe(recipe_data)
    assert created.id is not None
    assert created.title == "SQLite Test Recipe"
    assert created.cuisine == "Italian"
    
    # Retrieve the recipe
    retrieved = storage.get_recipe(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == "SQLite Test Recipe"
    assert retrieved.ingredients == ["water", "salt"]
    assert retrieved.instructions == ["Boil water", "Add salt"]
    assert retrieved.tags == ["test", "sqlite"]
    assert retrieved.cuisine == "Italian"

def test_sqlite_persistence_between_restarts(temp_db):
    # First instance creates the recipe
    storage1 = SQLiteRecipeStorage(db_path=temp_db)
    recipe_data = RecipeCreate(
        title="Persistent Recipe",
        description="Will survive restart",
        ingredients=["yeast", "flour"],
        instructions=["Mix yeast and flour"],
        tags=["bread"],
        cuisine="French"
    )
    created = storage1.create_recipe(recipe_data)
    recipe_id = created.id
    
    # Simulate application restart by creating a new storage instance pointing to the same db file
    storage2 = SQLiteRecipeStorage(db_path=temp_db)
    retrieved = storage2.get_recipe(recipe_id)
    assert retrieved is not None
    assert retrieved.title == "Persistent Recipe"
    assert retrieved.ingredients == ["yeast", "flour"]

def test_sqlite_search_recipes(temp_db):
    storage = SQLiteRecipeStorage(db_path=temp_db)
    
    r1 = storage.create_recipe(RecipeCreate(
        title="Apple Pie",
        description="Sweet pie",
        ingredients=["apple", "sugar"],
        instructions=["bake"],
        tags=["dessert"],
        cuisine="American"
    ))
    
    r2 = storage.create_recipe(RecipeCreate(
        title="Banana Bread",
        description="Sweet bread",
        ingredients=["banana", "sugar"],
        instructions=["bake"],
        tags=["dessert"],
        cuisine="American"
    ))
    
    # Query with non-empty string
    results = storage.search_recipes("Apple")
    assert len(results) == 1
    assert results[0].id == r1.id
    
    # Case insensitive check
    results_lower = storage.search_recipes("banana")
    assert len(results_lower) == 1
    assert results_lower[0].id == r2.id
    
    # Empty query returns all
    all_results = storage.search_recipes("")
    assert len(all_results) == 2

def test_sqlite_update_recipe(temp_db):
    storage = SQLiteRecipeStorage(db_path=temp_db)
    
    r = storage.create_recipe(RecipeCreate(
        title="Initial Recipe",
        description="To be updated",
        ingredients=["carrot"],
        instructions=["peel"],
        tags=["starter"],
        cuisine="Global"
    ))
    
    update_data = RecipeUpdate(
        title="Updated Recipe Title",
        description="Has been updated",
        ingredients=["carrot", "salt"],
        instructions=["peel", "boil"],
        tags=["side", "veggie"],
        cuisine="English"
    )
    
    updated = storage.update_recipe(r.id, update_data)
    assert updated is not None
    assert updated.title == "Updated Recipe Title"
    assert updated.ingredients == ["carrot", "salt"]
    assert updated.cuisine == "English"
    assert updated.updated_at > r.updated_at
    
    # Read from DB again to verify changes persisted
    retrieved = storage.get_recipe(r.id)
    assert retrieved.title == "Updated Recipe Title"
    assert retrieved.description == "Has been updated"

def test_sqlite_delete_recipe(temp_db):
    storage = SQLiteRecipeStorage(db_path=temp_db)
    
    r = storage.create_recipe(RecipeCreate(
        title="To Delete",
        description="Goodbye",
        ingredients=["ice"],
        instructions=["melt"],
        tags=["water"],
        cuisine="Arctic"
    ))
    
    assert storage.get_recipe(r.id) is not None
    
    deleted = storage.delete_recipe(r.id)
    assert deleted is True
    
    assert storage.get_recipe(r.id) is None
    
    # Deleting non-existent returns False
    assert storage.delete_recipe("fake-id") is False

def test_sqlite_import_recipes(temp_db):
    storage = SQLiteRecipeStorage(db_path=temp_db)
    
    # Seed a recipe first
    storage.create_recipe(RecipeCreate(
        title="Old Recipe",
        description="To be replaced",
        ingredients=["old"],
        instructions=["discard"],
        tags=["old"],
        cuisine="Global"
    ))
    
    import_data = [
        {
            "id": "imported-1",
            "title": "Imported Recipe 1",
            "description": "First imported",
            "ingredients": ["apple"],
            "instructions": ["eat"],
            "tags": ["fruit"],
            "cuisine": "Global",
            "created_at": "2026-06-05T10:00:00",
            "updated_at": "2026-06-05T10:00:00"
        },
        {
            "id": "imported-2",
            "title": "Imported Recipe 2",
            "description": "Second imported",
            "ingredients": ["pear"],
            "instructions": ["peel"],
            "tags": ["fruit"],
            "cuisine": "Global"
        }
    ]
    
    count = storage.import_recipes(import_data)
    assert count == 2
    
    # Verify the table was replaced
    all_recipes = storage.get_all_recipes()
    assert len(all_recipes) == 2
    
    titles = {r.title for r in all_recipes}
    assert "Imported Recipe 1" in titles
    assert "Imported Recipe 2" in titles
    assert "Old Recipe" not in titles
    
    # Check that imported-1 has correct parsed datetime
    r1 = storage.get_recipe("imported-1")
    assert isinstance(r1.created_at, datetime)
    assert r1.created_at.year == 2026
