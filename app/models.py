from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional, Dict
import uuid

# Constants
MAX_TITLE_LENGTH = 200
MAX_INGREDIENTS = 50


class Recipe(BaseModel):
    model_config = ConfigDict()

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    tags: List[str] = Field(default_factory=list)
    cuisine: str = Field(default="Global")
    owner_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecipeCreate(BaseModel):
    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    tags: List[str] = Field(default_factory=list)
    cuisine: str


class RecipeUpdate(BaseModel):
    title: str
    description: str
    ingredients: List[str]
    instructions: List[str]
    tags: List[str]
    cuisine: str


class User(BaseModel):
    id: str
    username: str
    email: str
    password_hash: str
    profile_name: Optional[str] = None
    preferences: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    profile_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    preferences: Optional[dict] = None


class Collection(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


# --- V2 Enhanced Recipe Models ---

class Nutrition(BaseModel):
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class Difficulty(BaseModel):
    level: str  # easy | medium | hard
    prep_time_minutes: int
    cook_time_minutes: int


class Relationships(BaseModel):
    substitutions: Dict[str, str] = Field(default_factory=dict)  # e.g., {"milk": "soy milk"}
    variations: List[str] = Field(default_factory=list)  # list of recipe IDs


class RecipeV2(Recipe):
    nutrition: Optional[Nutrition] = None
    dietary_restrictions: List[str] = Field(default_factory=list)
    difficulty: Optional[Difficulty] = None
    equipment: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    relationships: Optional[Relationships] = None


class RecipeV2Create(RecipeCreate):
    nutrition: Optional[Nutrition] = None
    dietary_restrictions: List[str] = Field(default_factory=list)
    difficulty: Optional[Difficulty] = None
    equipment: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    relationships: Optional[Relationships] = None


class RecipeV2Update(RecipeUpdate):
    nutrition: Optional[Nutrition] = None
    dietary_restrictions: List[str] = Field(default_factory=list)
    difficulty: Optional[Difficulty] = None
    equipment: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    relationships: Optional[Relationships] = None


