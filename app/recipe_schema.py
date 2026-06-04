"""
Recipe JSON Schema — the contract between the API and its consumers.

This schema defines exactly what data the API expects and returns.
Jamie's minimum requirements:
{
  "title": "Pasta Carbonara",
  "instructions": ["Step 1", "Step 2"],
  "cuisine": "Italian"
}

The full schema extends this with all fields our Recipe model supports.
"""

from jsonschema import validate


# The canonical JSON Schema for a recipe
RECIPE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Recipe",
    "description": "A recipe in the Recipe Explorer system",
    "type": "object",
    "required": ["title", "instructions", "cuisine"],
    "properties": {
        "id": {"type": "string", "description": "Unique identifier for the recipe"},
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Name of the recipe",
        },
        "description": {
            "type": "string",
            "description": "Brief description of the recipe",
        },
        "ingredients": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of ingredients with quantities",
        },
        "instructions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "Step-by-step cooking instructions",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Categorization tags",
        },
        "cuisine": {
            "type": "string",
            "minLength": 1,
            "description": "Cuisine type (e.g., Italian, Chinese, Mexican)",
        },
        "created_at": {"type": "string", "description": "ISO 8601 creation timestamp"},
        "updated_at": {
            "type": "string",
            "description": "ISO 8601 last-update timestamp",
        },
        "source": {
            "type": "string",
            "description": "Origin of the recipe (e.g., 'internal', 'mealdb')",
        },
        "image_url": {"type": "string", "description": "URL to recipe image"},
    },
    "additionalProperties": False,
}


def validate_recipe(data: dict) -> bool:
    """
    Validate a recipe dict against the JSON Schema.

    Returns True if valid, raises JsonSchemaValidationError if not.
    """
    validate(instance=data, schema=RECIPE_SCHEMA)
    return True


def get_schema() -> dict:
    """Return the canonical recipe JSON Schema."""
    return RECIPE_SCHEMA
