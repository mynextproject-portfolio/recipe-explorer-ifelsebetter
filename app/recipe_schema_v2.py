"""
Recipe V2 JSON Schema — the contract for API v2.
"""

from jsonschema import validate


RECIPE_SCHEMA_V2 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "RecipeV2",
    "description": "An enhanced recipe in the Recipe Explorer v2 system",
    "type": "object",
    "required": ["title", "instructions", "cuisine"],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string"},
        "ingredients": {"type": "array", "items": {"type": "string"}},
        "instructions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "tags": {"type": "array", "items": {"type": "string"}},
        "cuisine": {"type": "string", "minLength": 1},
        "owner_id": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "source": {"type": "string"},
        "image_url": {"type": ["string", "null"]},
        
        # Enhanced v2 fields
        "nutrition": {
            "type": ["object", "null"],
            "required": ["calories", "protein_g", "fat_g", "carbs_g"],
            "properties": {
                "calories": {"type": "number"},
                "protein_g": {"type": "number"},
                "fat_g": {"type": "number"},
                "carbs_g": {"type": "number"}
            },
            "additionalProperties": False
        },
        "dietary_restrictions": {"type": "array", "items": {"type": "string"}},
        "difficulty": {
            "type": ["object", "null"],
            "required": ["level", "prep_time_minutes", "cook_time_minutes"],
            "properties": {
                "level": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "prep_time_minutes": {"type": "integer", "minimum": 0},
                "cook_time_minutes": {"type": "integer", "minimum": 0}
            },
            "additionalProperties": False
        },
        "equipment": {"type": "array", "items": {"type": "string"}},
        "techniques": {"type": "array", "items": {"type": "string"}},
        "relationships": {
            "type": ["object", "null"],
            "properties": {
                "substitutions": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "variations": {"type": "array", "items": {"type": "string"}}
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False,
}


def validate_recipe_v2(data: dict) -> bool:
    """Validate data against RecipeV2 JSON Schema."""
    validate(instance=data, schema=RECIPE_SCHEMA_V2)
    return True


def get_schema_v2() -> dict:
    return RECIPE_SCHEMA_V2
