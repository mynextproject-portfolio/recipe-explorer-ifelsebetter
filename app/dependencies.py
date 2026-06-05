from typing import Optional
from app.services.interfaces import RecipeStorageInterface, CacheInterface, MealDBAdapterInterface
from app.services.sqlite_storage import SQLiteRecipeStorage
from app.services.cache import RedisCache
from app.services.mealdb_adapter import MealDBAdapter

# Default singletons
_storage: RecipeStorageInterface = SQLiteRecipeStorage()
_cache: CacheInterface = RedisCache()
_mealdb_adapter: MealDBAdapterInterface = MealDBAdapter(cache=_cache)


def set_dependencies(
    storage: Optional[RecipeStorageInterface] = None,
    cache: Optional[CacheInterface] = None,
    mealdb_adapter: Optional[MealDBAdapterInterface] = None,
) -> None:
    """Dynamically set concrete implementations for standard dependencies (e.g. at startup or during tests)."""
    global _storage, _cache, _mealdb_adapter
    if storage is not None:
        _storage = storage
    if cache is not None:
        _cache = cache
    if mealdb_adapter is not None:
        _mealdb_adapter = mealdb_adapter


def get_storage() -> RecipeStorageInterface:
    """Dependency provider for recipe storage."""
    return _storage


def get_cache() -> CacheInterface:
    """Dependency provider for redis cache."""
    return _cache


def get_mealdb_adapter() -> MealDBAdapterInterface:
    """Dependency provider for MealDB adapter."""
    return _mealdb_adapter
