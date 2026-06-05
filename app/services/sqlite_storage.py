"""
SQLite-backed recipe storage.

Implements RecipeStorageInterface with persistent SQLite storage.
Uses parameterized queries exclusively to prevent SQL injection.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models import (
    Recipe, RecipeCreate, RecipeUpdate,
    User, UserCreate, Collection, CollectionCreate
)
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
        """Create database tables and handle migrations."""
        conn = self._get_connection()
        try:
            # Create recipes table
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

            # Create users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    profile_name TEXT,
                    preferences TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create favorites table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, recipe_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create ratings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    user_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, recipe_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create collections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create collection_recipes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_recipes (
                    collection_id TEXT NOT NULL,
                    recipe_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (collection_id, recipe_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
                )
            """)

            # Migration: add owner_id column to recipes table if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(recipes)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "owner_id" not in columns:
                conn.execute("ALTER TABLE recipes ADD COLUMN owner_id TEXT REFERENCES users(id) ON DELETE SET NULL")

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
            owner_id=row["owner_id"] if "owner_id" in row.keys() else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


    def get_all_recipes(self, user_id: Optional[str] = None) -> List[Recipe]:
        """Retrieve all recipes from storage, optionally filtering by user access."""
        conn = self._get_connection()
        try:
            if user_id:
                cursor = conn.execute(
                    "SELECT * FROM recipes WHERE owner_id IS NULL OR owner_id = ?",
                    (user_id,),
                )
            else:
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

    def search_recipes(self, query: str, user_id: Optional[str] = None) -> List[Recipe]:
        """Search recipes based on a title query (case-insensitive)."""
        if not query:
            return self.get_all_recipes(user_id)

        conn = self._get_connection()
        try:
            if user_id:
                cursor = conn.execute(
                    "SELECT * FROM recipes WHERE title LIKE ? AND (owner_id IS NULL OR owner_id = ?)",
                    (f"%{query}%", user_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM recipes WHERE title LIKE ?",
                    (f"%{query}%",),
                )
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def create_recipe(self, recipe_data: RecipeCreate, owner_id: Optional[str] = None) -> Recipe:
        """Create a new recipe."""
        recipe = Recipe(**recipe_data.model_dump())
        recipe.owner_id = owner_id
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO recipes (id, title, description, ingredients,
                                     instructions, tags, cuisine, owner_id,
                                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe.id,
                    recipe.title,
                    recipe.description,
                    json.dumps(recipe.ingredients),
                    json.dumps(recipe.instructions),
                    json.dumps(recipe.tags),
                    recipe.cuisine,
                    recipe.owner_id,
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

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert a database row to a User model instance."""
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            profile_name=row["profile_name"],
            preferences=json.loads(row["preferences"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_collection(self, row: sqlite3.Row) -> Collection:
        """Convert a database row to a Collection model instance."""
        return Collection(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # --- User Management ---
    def create_user(self, user_data: UserCreate, password_hash: str) -> User:
        """Register a new user."""
        user_id = str(uuid.uuid4())
        now = datetime.now()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, profile_name, preferences, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_data.username,
                    user_data.email,
                    password_hash,
                    user_data.profile_name or user_data.username,
                    "{}",
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()
            return User(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                profile_name=user_data.profile_name or user_data.username,
                preferences={},
                created_at=now,
                updated_at=now,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username or email already exists") from exc
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Look up user by username."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Look up user by email."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def get_user(self, user_id: str) -> Optional[User]:
        """Look up user by unique ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def update_user_profile(
        self, user_id: str, profile_name: Optional[str], preferences: Optional[dict]
    ) -> Optional[User]:
        """Update user profile details and preferences."""
        user = self.get_user(user_id)
        if not user:
            return None

        if profile_name is not None:
            user.profile_name = profile_name
        if preferences is not None:
            user.preferences = preferences
        user.updated_at = datetime.now()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE users
                SET profile_name = ?, preferences = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    user.profile_name,
                    json.dumps(user.preferences),
                    user.updated_at.isoformat(),
                    user_id,
                ),
            )
            conn.commit()
            return user
        finally:
            conn.close()

    # --- Favorites ---
    def add_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Add a recipe to user's favorites."""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO favorites (user_id, recipe_id, created_at) VALUES (?, ?, ?)",
                (user_id, recipe_id, datetime.now().isoformat()),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def remove_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Remove a recipe from user's favorites."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?",
                (user_id, recipe_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_favorites(self, user_id: str) -> List[Recipe]:
        """Retrieve all recipes favorited by the user."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT r.* FROM recipes r
                JOIN favorites f ON r.id = f.recipe_id
                WHERE f.user_id = ?
                """,
                (user_id,),
            )
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def is_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Check if a specific recipe is favorited by the user."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND recipe_id = ?",
                (user_id, recipe_id),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    # --- Ratings ---
    def rate_recipe(self, user_id: str, recipe_id: str, rating: int) -> bool:
        """Rate a recipe (1-5 stars). Updates existing rating if it exists."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO ratings (user_id, recipe_id, rating, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, recipe_id) DO UPDATE SET rating=excluded.rating, created_at=excluded.created_at
                """,
                (user_id, recipe_id, rating, datetime.now().isoformat()),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_recipe_rating_stats(self, recipe_id: str) -> dict:
        """Get average rating and total count for a recipe."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT AVG(rating) as avg_rating, COUNT(rating) as rating_count FROM ratings WHERE recipe_id = ?",
                (recipe_id,),
            )
            row = cursor.fetchone()
            avg = row["avg_rating"] if row and row["avg_rating"] is not None else 0.0
            cnt = row["rating_count"] if row and row["rating_count"] is not None else 0
            return {"average": round(float(avg), 1), "count": int(cnt)}
        finally:
            conn.close()

    def get_user_rating(self, user_id: str, recipe_id: str) -> Optional[int]:
        """Get the user's rating for a specific recipe."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT rating FROM ratings WHERE user_id = ? AND recipe_id = ?",
                (user_id, recipe_id),
            )
            row = cursor.fetchone()
            return int(row["rating"]) if row else None
        finally:
            conn.close()

    # --- Collections ---
    def create_collection(self, user_id: str, collection_data: CollectionCreate) -> Collection:
        """Create a new personal recipe collection."""
        collection_id = str(uuid.uuid4())
        now = datetime.now()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO collections (id, user_id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_id,
                    user_id,
                    collection_data.name,
                    collection_data.description,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()
            return Collection(
                id=collection_id,
                user_id=user_id,
                name=collection_data.name,
                description=collection_data.description,
                created_at=now,
                updated_at=now,
            )
        finally:
            conn.close()

    def get_collections(self, user_id: str) -> List[Collection]:
        """List all collections created by the user."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM collections WHERE user_id = ? ORDER BY name ASC", (user_id,))
            return [self._row_to_collection(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Retrieve details of a specific collection."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
            row = cursor.fetchone()
            return self._row_to_collection(row) if row else None
        finally:
            conn.close()

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def add_recipe_to_collection(self, collection_id: str, recipe_id: str) -> bool:
        """Add a recipe to a collection."""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO collection_recipes (collection_id, recipe_id, created_at) VALUES (?, ?, ?)",
                (collection_id, recipe_id, datetime.now().isoformat()),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def remove_recipe_from_collection(self, collection_id: str, recipe_id: str) -> bool:
        """Remove a recipe from a collection."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM collection_recipes WHERE collection_id = ? AND recipe_id = ?",
                (collection_id, recipe_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_collection_recipes(self, collection_id: str) -> List[Recipe]:
        """Retrieve all recipes in a collection."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT r.* FROM recipes r
                JOIN collection_recipes cr ON r.id = cr.recipe_id
                WHERE cr.collection_id = ?
                """,
                (collection_id,),
            )
            return [self._row_to_recipe(row) for row in cursor.fetchall()]
        finally:
            conn.close()

