"""
Tests for Recipe JSON Schema validation.

Verifies that the schema enforces Jamie's contract:
  - title, instructions (array), and cuisine are required
  - instructions must be an array of strings, not a text block
  - the /api/schema endpoint returns the schema
"""

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError

from app.recipe_schema import validate_recipe, get_schema


class TestRecipeSchemaValidation:
    """Unit tests for the schema validation function."""

    def test_valid_recipe_passes_schema(self):
        """Jamie's example recipe passes schema validation."""
        recipe = {
            "title": "Pasta Carbonara",
            "instructions": ["Step 1", "Step 2"],
            "cuisine": "Italian",
        }
        assert validate_recipe(recipe) is True

    def test_full_recipe_passes_schema(self):
        """A recipe with all fields passes validation."""
        recipe = {
            "id": "test-123",
            "title": "Classic Quebec Poutine",
            "description": "Canada's national dish.",
            "ingredients": ["4 large potatoes", "2 cups cheese curds"],
            "instructions": ["Cut potatoes.", "Fry until golden."],
            "tags": ["comfort food", "Canadian"],
            "cuisine": "Canadian",
            "source": "internal",
            "image_url": "https://example.com/poutine.jpg",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-15T10:30:00",
        }
        assert validate_recipe(recipe) is True

    def test_missing_title_fails(self):
        """Missing required 'title' field fails validation."""
        recipe = {
            "instructions": ["Step 1"],
            "cuisine": "Italian",
        }
        with pytest.raises(
            JsonSchemaValidationError, match="'title' is a required property"
        ):
            validate_recipe(recipe)

    def test_missing_instructions_fails(self):
        """Missing required 'instructions' field fails validation."""
        recipe = {
            "title": "Pasta Carbonara",
            "cuisine": "Italian",
        }
        with pytest.raises(
            JsonSchemaValidationError, match="'instructions' is a required property"
        ):
            validate_recipe(recipe)

    def test_missing_cuisine_fails(self):
        """Missing required 'cuisine' field fails validation."""
        recipe = {
            "title": "Pasta Carbonara",
            "instructions": ["Step 1"],
        }
        with pytest.raises(
            JsonSchemaValidationError, match="'cuisine' is a required property"
        ):
            validate_recipe(recipe)

    def test_instructions_must_be_array(self):
        """Instructions as a string (not array) fails — enforces array format."""
        recipe = {
            "title": "Pasta Carbonara",
            "instructions": "Step 1. Step 2.",  # String, not array!
            "cuisine": "Italian",
        }
        with pytest.raises(JsonSchemaValidationError):
            validate_recipe(recipe)

    def test_instructions_must_have_at_least_one_step(self):
        """Empty instructions array fails validation."""
        recipe = {
            "title": "Pasta Carbonara",
            "instructions": [],
            "cuisine": "Italian",
        }
        with pytest.raises(JsonSchemaValidationError):
            validate_recipe(recipe)

    def test_title_max_length(self):
        """Title exceeding 200 characters fails validation."""
        recipe = {
            "title": "A" * 201,
            "instructions": ["Step 1"],
            "cuisine": "Italian",
        }
        with pytest.raises(JsonSchemaValidationError):
            validate_recipe(recipe)

    def test_empty_title_fails(self):
        """Empty string title fails validation."""
        recipe = {
            "title": "",
            "instructions": ["Step 1"],
            "cuisine": "Italian",
        }
        with pytest.raises(JsonSchemaValidationError):
            validate_recipe(recipe)

    def test_additional_properties_rejected(self):
        """Unknown fields are rejected (strict contract)."""
        recipe = {
            "title": "Test",
            "instructions": ["Step 1"],
            "cuisine": "Italian",
            "unknown_field": "bad",
        }
        with pytest.raises(JsonSchemaValidationError):
            validate_recipe(recipe)


class TestGetSchema:
    """Test the schema retrieval function."""

    def test_get_schema_returns_dict(self):
        """get_schema returns a valid JSON Schema dict."""
        schema = get_schema()
        assert isinstance(schema, dict)
        assert schema["title"] == "Recipe"
        assert "properties" in schema
        assert "required" in schema

    def test_schema_has_required_fields(self):
        """Schema requires title, instructions, and cuisine."""
        schema = get_schema()
        assert "title" in schema["required"]
        assert "instructions" in schema["required"]
        assert "cuisine" in schema["required"]


class TestSchemaEndpoint:
    """Test the /api/schema endpoint."""

    def test_schema_endpoint_returns_valid_schema(self, client):
        """GET /api/schema returns the JSON Schema."""
        response = client.get("/api/schema")
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Recipe"
        assert "properties" in data
        assert "title" in data["properties"]
        assert "instructions" in data["properties"]
        assert "cuisine" in data["properties"]
