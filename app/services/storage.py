from typing import Dict, List, Optional
from datetime import datetime
import uuid
from app.models import (
    Recipe, RecipeCreate, RecipeUpdate,
    User, UserCreate, Collection, CollectionCreate
)

# Global counter for analytics (can be used for analytics)
recipe_view_count = {}


from app.services.interfaces import RecipeStorageInterface


class RecipeStorage(RecipeStorageInterface):
    def __init__(self):
        self.recipes: Dict[str, Recipe] = {}
        self.users: Dict[str, User] = {}
        self.favorites: Dict[str, List[str]] = {}  # user_id -> list of recipe_ids
        self.ratings: Dict[str, Dict[str, int]] = {}  # recipe_id -> {user_id: rating}
        self.collections: Dict[str, Collection] = {}  # id -> Collection
        self.collection_recipes: Dict[str, List[str]] = {}  # collection_id -> list of recipe_ids

    def get_all_recipes(self, user_id: Optional[str] = None) -> List[Recipe]:
        if user_id:
            return [r for r in self.recipes.values() if r.owner_id is None or r.owner_id == user_id]
        return list(self.recipes.values())

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        return self.recipes.get(recipe_id)

    def search_recipes(self, query: str, user_id: Optional[str] = None) -> List[Recipe]:
        if not query:
            return self.get_all_recipes(user_id)

        # Case-insensitive title search
        query_lower = query.lower()
        results = []
        for recipe in self.get_all_recipes(user_id):
            if query_lower in recipe.title.lower():
                results.append(recipe)
        return results

    def create_recipe(self, recipe_data: RecipeCreate, owner_id: Optional[str] = None) -> Recipe:
        recipe = Recipe(**recipe_data.model_dump())
        recipe.owner_id = owner_id
        self.recipes[recipe.id] = recipe
        return recipe

    def update_recipe(
        self, recipe_id: str, recipe_data: RecipeUpdate
    ) -> Optional[Recipe]:
        if recipe_id not in self.recipes:
            return None

        recipe = self.recipes[recipe_id]
        updated_data = recipe_data.model_dump()
        for key, value in updated_data.items():
            setattr(recipe, key, value)
        recipe.updated_at = datetime.now()

        self.recipes[recipe_id] = recipe
        return recipe

    def delete_recipe(self, recipe_id: str) -> bool:
        if recipe_id in self.recipes:
            del self.recipes[recipe_id]
            return True
        return False

    def import_recipes(self, recipes_data: List[dict]) -> int:
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

        # Replace all existing recipes
        self.recipes.clear()
        self.recipes.update(new_recipes)
        return len(new_recipes)

    # --- User Management ---
    def create_user(self, user_data: UserCreate, password_hash: str) -> User:
        for u in self.users.values():
            if u.username == user_data.username or u.email == user_data.email:
                raise ValueError("Username or email already exists")
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            profile_name=user_data.profile_name or user_data.username,
            preferences={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.users[user_id] = user
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        for u in self.users.values():
            if u.username == username:
                return u
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        for u in self.users.values():
            if u.email == email:
                return u
        return None

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def update_user_profile(
        self, user_id: str, profile_name: Optional[str], preferences: Optional[dict]
    ) -> Optional[User]:
        user = self.get_user(user_id)
        if not user:
            return None
        if profile_name is not None:
            user.profile_name = profile_name
        if preferences is not None:
            user.preferences = preferences
        user.updated_at = datetime.now()
        return user

    # --- Favorites ---
    def add_favorite(self, user_id: str, recipe_id: str) -> bool:
        if user_id not in self.favorites:
            self.favorites[user_id] = []
        if recipe_id not in self.favorites[user_id]:
            self.favorites[user_id].append(recipe_id)
        return True

    def remove_favorite(self, user_id: str, recipe_id: str) -> bool:
        if user_id in self.favorites and recipe_id in self.favorites[user_id]:
            self.favorites[user_id].remove(recipe_id)
            return True
        return False

    def get_favorites(self, user_id: str) -> List[Recipe]:
        fav_ids = self.favorites.get(user_id, [])
        return [self.recipes[rid] for rid in fav_ids if rid in self.recipes]

    def is_favorite(self, user_id: str, recipe_id: str) -> bool:
        return recipe_id in self.favorites.get(user_id, [])

    # --- Ratings ---
    def rate_recipe(self, user_id: str, recipe_id: str, rating: int) -> bool:
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be 1-5")
        if recipe_id not in self.ratings:
            self.ratings[recipe_id] = {}
        self.ratings[recipe_id][user_id] = rating
        return True

    def get_recipe_rating_stats(self, recipe_id: str) -> dict:
        user_ratings = self.ratings.get(recipe_id, {})
        if not user_ratings:
            return {"average": 0.0, "count": 0}
        avg = sum(user_ratings.values()) / len(user_ratings)
        return {"average": round(avg, 1), "count": len(user_ratings)}

    def get_user_rating(self, user_id: str, recipe_id: str) -> Optional[int]:
        return self.ratings.get(recipe_id, {}).get(user_id)

    # --- Collections ---
    def create_collection(self, user_id: str, collection_data: CollectionCreate) -> Collection:
        cid = str(uuid.uuid4())
        col = Collection(
            id=cid,
            user_id=user_id,
            name=collection_data.name,
            description=collection_data.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.collections[cid] = col
        self.collection_recipes[cid] = []
        return col

    def get_collections(self, user_id: str) -> List[Collection]:
        return [c for c in self.collections.values() if c.user_id == user_id]

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        return self.collections.get(collection_id)

    def delete_collection(self, collection_id: str) -> bool:
        if collection_id in self.collections:
            del self.collections[collection_id]
            if collection_id in self.collection_recipes:
                del self.collection_recipes[collection_id]
            return True
        return False

    def add_recipe_to_collection(self, collection_id: str, recipe_id: str) -> bool:
        if collection_id in self.collection_recipes:
            if recipe_id not in self.collection_recipes[collection_id]:
                self.collection_recipes[collection_id].append(recipe_id)
            return True
        return False

    def remove_recipe_from_collection(self, collection_id: str, recipe_id: str) -> bool:
        if collection_id in self.collection_recipes and recipe_id in self.collection_recipes[collection_id]:
            self.collection_recipes[collection_id].remove(recipe_id)
            return True
        return False

    def get_collection_recipes(self, collection_id: str) -> List[Recipe]:
        rids = self.collection_recipes.get(collection_id, [])
        return [self.recipes[rid] for rid in rids if rid in self.recipes]


# Global storage instance (intentionally simple for refactoring)
recipe_storage = RecipeStorage()
