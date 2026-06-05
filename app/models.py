from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional
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

