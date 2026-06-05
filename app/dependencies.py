from typing import Optional
from fastapi import Request, HTTPException, Depends
from app.services.interfaces import RecipeStorageInterface, CacheInterface, MealDBAdapterInterface
from app.services.sqlite_storage import SQLiteRecipeStorage
from app.services.cache import RedisCache
from app.services.mealdb_adapter import MealDBAdapter
from app.models import User
from app.services.auth import verify_access_token

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


async def get_current_user(
    request: Request,
    storage: RecipeStorageInterface = Depends(get_storage),
    cache: CacheInterface = Depends(get_cache),
) -> User:
    """
    Retrieve the currently authenticated user from the JWT cookie.
    Raises 401 Unauthorized if verification fails or session is revoked.
    """
    token = request.cookies.get("__Secure-session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jti = payload.get("jti")
    if jti:
        # Check Redis blacklist
        if cache.get(f"blacklist:{jti}"):
            raise HTTPException(status_code=401, detail="Session expired or logged out")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_optional_current_user(
    request: Request,
    storage: RecipeStorageInterface = Depends(get_storage),
    cache: CacheInterface = Depends(get_cache),
) -> Optional[User]:
    """
    Retrieve the user if authenticated, otherwise returns None gracefully.
    """
    try:
        return await get_current_user(request, storage, cache)
    except HTTPException:
        return None


async def verify_csrf_token(request: Request) -> None:
    """
    Verifies the Double-Submit CSRF cookie against the request header.
    Applies only to state-changing operations (POST, PUT, DELETE, PATCH).
    """
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(status_code=403, detail="CSRF token mismatch or missing")

