from typing import Dict, List, Optional
from datetime import datetime
import uuid
from app.models import (
    Recipe, RecipeCreate, RecipeUpdate,
    User, UserCreate, Collection, CollectionCreate,
    RecipeV2, RecipeV2Create, RecipeV2Update,
    Nutrition, Difficulty, Relationships
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

    # --- V2 API Methods ---
    def _upgrade_to_v2(self, r: Recipe) -> RecipeV2:
        return RecipeV2(
            id=r.id,
            title=r.title,
            description=r.description,
            ingredients=r.ingredients,
            instructions=r.instructions,
            tags=r.tags,
            cuisine=r.cuisine,
            owner_id=r.owner_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
            nutrition=getattr(r, 'nutrition', None),
            dietary_restrictions=getattr(r, 'dietary_restrictions', []),
            difficulty=getattr(r, 'difficulty', None),
            equipment=getattr(r, 'equipment', []),
            techniques=getattr(r, 'techniques', []),
            relationships=getattr(r, 'relationships', None),
        )

    def get_all_recipes_v2(
        self, 
        user_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        dietary: Optional[str] = None,
        cuisine: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc"
    ) -> List[RecipeV2]:
        """Retrieve all v2 recipes with optional filters and sorting."""
        res = []
        for r in self.recipes.values():
            if user_id and r.owner_id is not None and r.owner_id != user_id:
                continue
            if difficulty:
                if not hasattr(r, 'difficulty') or not r.difficulty or r.difficulty.level != difficulty:
                    continue
            if dietary:
                if not hasattr(r, 'dietary_restrictions') or not r.dietary_restrictions or dietary not in r.dietary_restrictions:
                    continue
            if cuisine:
                if r.cuisine != cuisine:
                    continue
            
            if not isinstance(r, RecipeV2):
                res.append(self._upgrade_to_v2(r))
            else:
                res.append(r)
        
        if sort_by:
            def get_sort_key(recipe: RecipeV2):
                if sort_by == "title":
                    return recipe.title.lower()
                elif sort_by == "created_at":
                    return recipe.created_at
                elif sort_by == "updated_at":
                    return recipe.updated_at
                elif sort_by == "prep_time":
                    return recipe.difficulty.prep_time_minutes if recipe.difficulty else 0
                elif sort_by == "cook_time":
                    return recipe.difficulty.cook_time_minutes if recipe.difficulty else 0
                elif sort_by == "calories":
                    return recipe.nutrition.calories if recipe.nutrition else 0.0
                return recipe.created_at
            
            reverse = (sort_order and sort_order.lower() == "desc")
            res.sort(key=get_sort_key, reverse=reverse)
        else:
            res.sort(key=lambda x: x.created_at, reverse=True)
            
        return res

    def get_recipe_v2(self, recipe_id: str) -> Optional[RecipeV2]:
        """Retrieve a specific v2 recipe by its ID."""
        r = self.recipes.get(recipe_id)
        if r is None:
            return None
        if not isinstance(r, RecipeV2):
            return self._upgrade_to_v2(r)
        return r

    def search_recipes_v2(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        dietary: Optional[str] = None,
        cuisine: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "asc"
    ) -> List[RecipeV2]:
        """Search v2 recipes with query, optional filters, and sorting."""
        all_v2 = self.get_all_recipes_v2(
            user_id=user_id,
            difficulty=difficulty,
            dietary=dietary,
            cuisine=cuisine,
            sort_by=sort_by,
            sort_order=sort_order
        )
        if not query:
            return all_v2
        
        query_lower = query.lower()
        return [r for r in all_v2 if query_lower in r.title.lower()]

    def create_recipe_v2(self, recipe_data: RecipeV2Create, owner_id: Optional[str] = None) -> RecipeV2:
        """Create a new v2 recipe."""
        recipe = RecipeV2.model_validate({**recipe_data.model_dump(), "owner_id": owner_id})
        self.recipes[recipe.id] = recipe
        return recipe

    def update_recipe_v2(self, recipe_id: str, recipe_data: RecipeV2Update) -> Optional[RecipeV2]:
        """Update an existing v2 recipe."""
        if recipe_id not in self.recipes:
            return None
        r = self.recipes[recipe_id]
        existing = r if isinstance(r, RecipeV2) else self._upgrade_to_v2(r)
        
        merged = {**existing.model_dump(), **recipe_data.model_dump(exclude_unset=True)}
        existing = RecipeV2.model_validate(merged)
        existing.updated_at = datetime.now()
        
        self.recipes[recipe_id] = existing
        return existing


    # --- Bulk Operations ---
    def create_recipes_bulk(self, recipes_data: List[RecipeV2Create], owner_id: Optional[str] = None) -> List[RecipeV2]:
        """Bulk create multiple v2 recipes."""
        from typing import List
        res = []
        for d in recipes_data:
            recipe = self.create_recipe_v2(d, owner_id)
            res.append(recipe)
        return res

    def update_recipes_bulk(self, updates: List[Tuple[str, RecipeV2Update]]) -> List[RecipeV2]:
        """Bulk update multiple v2 recipes."""
        from typing import List, Tuple
        res = []
        for rid, _ in updates:
            if rid not in self.recipes:
                raise ValueError(f"Recipe with ID {rid} not found")
        for rid, data in updates:
            updated = self.update_recipe_v2(rid, data)
            if updated:
                res.append(updated)
        return res

    def delete_recipes_bulk(self, recipe_ids: List[str]) -> int:
        """Bulk delete multiple recipes by ID. Returns count of deleted recipes."""
        from typing import List
        count = 0
        for rid in recipe_ids:
            if rid in self.recipes:
                del self.recipes[rid]
                count += 1
        return count



# Global storage instance (intentionally simple for refactoring)
recipe_storage = RecipeStorage()
