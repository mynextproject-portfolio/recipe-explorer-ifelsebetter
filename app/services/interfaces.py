from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple
from app.models import Recipe, RecipeCreate, RecipeUpdate

class RecipeStorageInterface(ABC):
    @abstractmethod
    def get_all_recipes(self) -> List[Recipe]:
        """Retrieve all recipes from storage."""
        pass

    @abstractmethod
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a specific recipe by its ID."""
        pass

    @abstractmethod
    def search_recipes(self, query: str) -> List[Recipe]:
        """Search recipes based on a title query."""
        pass

    @abstractmethod
    def create_recipe(self, recipe_data: RecipeCreate) -> Recipe:
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
