from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple
from app.models import (
    Recipe, RecipeCreate, RecipeUpdate,
    User, UserCreate, Collection, CollectionCreate
)

class RecipeStorageInterface(ABC):
    @abstractmethod
    def get_all_recipes(self, user_id: Optional[str] = None) -> List[Recipe]:
        """Retrieve all recipes from storage, optionally filtering by user access."""
        pass

    @abstractmethod
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a specific recipe by its ID."""
        pass

    @abstractmethod
    def search_recipes(self, query: str, user_id: Optional[str] = None) -> List[Recipe]:
        """Search recipes based on a title query."""
        pass

    @abstractmethod
    def create_recipe(self, recipe_data: RecipeCreate, owner_id: Optional[str] = None) -> Recipe:
        """Create a new recipe."""
        pass

    @abstractmethod
    def update_recipe(
        self, recipe_id: str, recipe_data: RecipeUpdate
    ) -> Optional[Recipe]:
        """Update an existing recipe."""
        pass

    @abstractmethod
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from storage."""
        pass

    @abstractmethod
    def import_recipes(self, recipes_data: List[dict]) -> int:
        """Import recipes from raw JSON data, replacing the current set."""
        pass

    # --- User Management ---
    @abstractmethod
    def create_user(self, user_data: UserCreate, password_hash: str) -> User:
        """Register a new user."""
        pass

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Look up user by username."""
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Look up user by email."""
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[User]:
        """Look up user by unique ID."""
        pass

    @abstractmethod
    def update_user_profile(
        self, user_id: str, profile_name: Optional[str], preferences: Optional[dict]
    ) -> Optional[User]:
        """Update user profile details and preferences."""
        pass

    # --- Favorites ---
    @abstractmethod
    def add_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Add a recipe to user's favorites."""
        pass

    @abstractmethod
    def remove_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Remove a recipe from user's favorites."""
        pass

    @abstractmethod
    def get_favorites(self, user_id: str) -> List[Recipe]:
        """Retrieve all recipes favorited by the user."""
        pass

    @abstractmethod
    def is_favorite(self, user_id: str, recipe_id: str) -> bool:
        """Check if a specific recipe is favorited by the user."""
        pass

    # --- Ratings ---
    @abstractmethod
    def rate_recipe(self, user_id: str, recipe_id: str, rating: int) -> bool:
        """Rate a recipe (1-5 stars). Updates existing rating if it exists."""
        pass

    @abstractmethod
    def get_recipe_rating_stats(self, recipe_id: str) -> dict:
        """Get average rating and total count for a recipe."""
        pass

    @abstractmethod
    def get_user_rating(self, user_id: str, recipe_id: str) -> Optional[int]:
        """Get the user's rating for a specific recipe."""
        pass

    # --- Collections ---
    @abstractmethod
    def create_collection(self, user_id: str, collection_data: CollectionCreate) -> Collection:
        """Create a new personal recipe collection."""
        pass

    @abstractmethod
    def get_collections(self, user_id: str) -> List[Collection]:
        """List all collections created by the user."""
        pass

    @abstractmethod
    def get_collection(self, collection_id: str) -> Optional[Collection]:
        """Retrieve details of a specific collection."""
        pass

    @abstractmethod
    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection."""
        pass

    @abstractmethod
    def add_recipe_to_collection(self, collection_id: str, recipe_id: str) -> bool:
        """Add a recipe to a collection."""
        pass

    @abstractmethod
    def remove_recipe_from_collection(self, collection_id: str, recipe_id: str) -> bool:
        """Remove a recipe from a collection."""
        pass

    @abstractmethod
    def get_collection_recipes(self, collection_id: str) -> List[Recipe]:
        """Retrieve all recipes in a collection."""
        pass



class CacheInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store a value in cache with a TTL."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the cache service is available."""
        pass


class MealDBAdapterInterface(ABC):
    @abstractmethod
    async def search_by_name(self, name: str) -> Tuple[List[dict], bool]:
        """Search for meals on the external API by name."""
        pass

    @abstractmethod
    async def get_by_id(self, meal_id: str) -> Optional[dict]:
        """Retrieve a specific meal from the external API by its ID."""
        pass
