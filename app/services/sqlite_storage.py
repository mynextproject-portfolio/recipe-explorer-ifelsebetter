"""
SQLite-backed recipe storage.

Implements RecipeStorageInterface with persistent SQLite storage.
Uses parameterized queries exclusively to prevent SQL injection.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models import Recipe, RecipeCreate, RecipeUpdate
from app.services.interfaces import RecipeStorageInterface

# Default database path — relative to project root
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "recipes.db"


class SQLiteRecipeStorage(RecipeStorageInterface):
    """Persistent recipe storage backed by SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = str(db_path) if db_path else str(DEFAULT_DB_PATH)
        self._ensure_directory()
        self._init_db()

    def _ensure_directory(self) -> None:
        """Create the parent directory for the database file if it doesn't exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new connection with row factory enabled."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """Create the recipes table if it doesn't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ingredients TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    cuisine TEXT NOT NULL DEFAULT 'Global',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _row_to_recipe(self, row: sqlite3.Row) -> Recipe:
        """Convert a database row to a Recipe model instance."""
        return Recipe(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            ingredients=json.loads(row["ingredients"]),
            instructions=json.loads(row["instructions"]),
            tags=json.loads(row["tags"]),
            cuisine=row["cuisine"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get_all_recipes(self) -> List[Recipe]:
        """Retrieve all recipes from storage."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM recipes")
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a specific recipe by its ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
            )
            row = cursor.fetchone()
            return self._row_to_recipe(row) if row else None
        finally:
            conn.close()

    def search_recipes(self, query: str) -> List[Recipe]:
        """Search recipes based on a title query (case-insensitive)."""
        if not query:
            return self.get_all_recipes()

        conn = self._get_connection()
        try:
            # Use parameterized LIKE for case-insensitive search
            cursor = conn.execute(
                "SELECT * FROM recipes WHERE title LIKE ?",
                (f"%{query}%",),
            )
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def create_recipe(self, recipe_data: RecipeCreate) -> Recipe:
        """Create a new recipe."""
        recipe = Recipe(**recipe_data.model_dump())
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO recipes (id, title, description, ingredients,
                                     instructions, tags, cuisine,
                                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe.id,
                    recipe.title,
                    recipe.description,
                    json.dumps(recipe.ingredients),
                    json.dumps(recipe.instructions),
                    json.dumps(recipe.tags),
                    recipe.cuisine,
                    recipe.created_at.isoformat(),
                    recipe.updated_at.isoformat(),
                ),
            )
            conn.commit()
            return recipe
        finally:
            conn.close()

    def update_recipe(
        self, recipe_id: str, recipe_data: RecipeUpdate
    ) -> Optional[Recipe]:
        """Update an existing recipe."""
        existing = self.get_recipe(recipe_id)
        if existing is None:
            return None

        updated_data = recipe_data.model_dump()
        for key, value in updated_data.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE recipes
                SET title = ?, description = ?, ingredients = ?,
                    instructions = ?, tags = ?, cuisine = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    existing.title,
                    existing.description,
                    json.dumps(existing.ingredients),
                    json.dumps(existing.instructions),
                    json.dumps(existing.tags),
                    existing.cuisine,
                    existing.updated_at.isoformat(),
                    recipe_id,
                ),
            )
            conn.commit()
            return existing
        finally:
            conn.close()

    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from storage."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM recipes WHERE id = ?", (recipe_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def import_recipes(self, recipes_data: List[dict]) -> int:
        """Import recipes from raw JSON data, replacing the current set."""
        from pydantic import ValidationError

        new_recipes = {}
        errors = []

        for i, recipe_dict in enumerate(recipes_data):
            try:
                # Handle datetime strings if they exist
                if "created_at" in recipe_dict and isinstance(
                    recipe_dict["created_at"], str
                ):
                    recipe_dict["created_at"] = datetime.fromisoformat(
                        recipe_dict["created_at"]
                    )
                if "updated_at" in recipe_dict and isinstance(
                    recipe_dict["updated_at"], str
                ):
                    recipe_dict["updated_at"] = datetime.fromisoformat(
                        recipe_dict["updated_at"]
                    )

                recipe = Recipe(**recipe_dict)
                new_recipes[recipe.id] = recipe
            except ValidationError as e:
                errors.append(f"Recipe at index {i} failed validation: {e}")
            except Exception as e:
                errors.append(f"Recipe at index {i} caused error: {e}")

        if errors:
            raise ValueError(
                "Validation failed for one or more recipes:\n" + "\n".join(errors)
            )

        # Replace all existing recipes atomically
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM recipes")
            for recipe in new_recipes.values():
                conn.execute(
                    """
                    INSERT INTO recipes (id, title, description, ingredients,
                                         instructions, tags, cuisine,
                                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        recipe.id,
                        recipe.title,
                        recipe.description,
                        json.dumps(recipe.ingredients),
                        json.dumps(recipe.instructions),
                        json.dumps(recipe.tags),
                        recipe.cuisine,
                        recipe.created_at.isoformat(),
                        recipe.updated_at.isoformat(),
                    ),
                )
            conn.commit()
            return len(new_recipes)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
