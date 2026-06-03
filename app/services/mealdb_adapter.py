"""
TheMealDB Adapter — transforms external API responses into our recipe schema.

TheMealDB returns ingredients as separate fields (strIngredient1..20) and
instructions as a single text block. This adapter parses and transforms
that into our array-based format.

Error Handling Strategy:
- Network timeout (>5s): return empty results + log warning
- HTTP 429 (rate limit): return empty results + log warning
- Invalid JSON: return empty results + log error
- Unexpected format: return empty results + log warning
- Individual meal transform failure: skip that meal, continue with others
"""
import logging
import re
from typing import Optional

import httpx

from app.recipe_schema import validate_recipe
from jsonschema import ValidationError as JsonSchemaValidationError

logger = logging.getLogger(__name__)

# TheMealDB free tier base URL (no API key needed)
DEFAULT_BASE_URL = "https://www.themealdb.com/api/json/v1/1"
DEFAULT_TIMEOUT = 5.0  # seconds


class MealDBAdapter:
    """Adapter for TheMealDB external API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search_by_name(self, name: str) -> list[dict]:
        """
        Search TheMealDB for meals matching a name.

        Returns a list of transformed recipe dicts, or an empty list
        if the API is unreachable or returns no results.
        """
        if not name or not name.strip():
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/search.php",
                    params={"s": name.strip()},
                )

            if response.status_code == 429:
                logger.warning("TheMealDB rate limited (429). Returning empty results.")
                return []

            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException:
            logger.warning("TheMealDB request timed out after %ss.", self.timeout)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning("TheMealDB HTTP error %s: %s", exc.response.status_code, exc)
            return []
        except httpx.RequestError as exc:
            logger.warning("TheMealDB network error: %s", exc)
            return []
        except ValueError:
            logger.error("TheMealDB returned invalid JSON.")
            return []

        return self._parse_meals_response(data)

    async def get_by_id(self, meal_id: str) -> Optional[dict]:
        """
        Look up a specific meal from TheMealDB by its ID.

        Returns a transformed recipe dict, or None if not found.
        """
        if not meal_id or not meal_id.strip():
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/lookup.php",
                    params={"i": meal_id.strip()},
                )

            if response.status_code == 429:
                logger.warning("TheMealDB rate limited (429).")
                return None

            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException:
            logger.warning("TheMealDB lookup timed out after %ss.", self.timeout)
            return None
        except httpx.HTTPStatusError as exc:
            logger.warning("TheMealDB HTTP error %s: %s", exc.response.status_code, exc)
            return None
        except httpx.RequestError as exc:
            logger.warning("TheMealDB network error: %s", exc)
            return None
        except ValueError:
            logger.error("TheMealDB returned invalid JSON for lookup.")
            return None

        meals = self._parse_meals_response(data)
        return meals[0] if meals else None

    def _parse_meals_response(self, data: dict) -> list[dict]:
        """
        Parse the top-level TheMealDB response and transform each meal.

        TheMealDB wraps results in {"meals": [...]} — if the key is missing
        or null, returns an empty list.
        """
        if not isinstance(data, dict):
            logger.warning("TheMealDB response is not a dict: %s", type(data))
            return []

        raw_meals = data.get("meals")
        if not raw_meals:
            # TheMealDB returns {"meals": null} when no results found
            return []

        if not isinstance(raw_meals, list):
            logger.warning("TheMealDB 'meals' is not a list: %s", type(raw_meals))
            return []

        results = []
        for raw_meal in raw_meals:
            try:
                transformed = self._transform_meal(raw_meal)
                if transformed:
                    results.append(transformed)
            except Exception as exc:
                meal_name = raw_meal.get("strMeal", "Unknown") if isinstance(raw_meal, dict) else "Unknown"
                logger.warning(
                    "Failed to transform meal '%s': %s", meal_name, exc
                )
                continue

        return results

    def _transform_meal(self, raw: dict) -> Optional[dict]:
        """
        Transform a single TheMealDB meal dict into our recipe schema.

        TheMealDB format:
            strIngredient1..20 — separate fields for each ingredient
            strMeasure1..20   — separate fields for each measurement
            strInstructions   — single text block

        Our format:
            ingredients: ["1 cup flour", "2 eggs", ...]
            instructions: ["Preheat oven to 350°F.", "Mix dry ingredients.", ...]
        """
        if not isinstance(raw, dict):
            return None

        # --- Collect ingredients ---
        ingredients = self._extract_ingredients(raw)

        # --- Parse instructions ---
        instructions = self._parse_instructions(raw.get("strInstructions", ""))

        if not instructions:
            # If we can't parse any instructions, the recipe isn't useful
            logger.debug("Skipping meal with no parseable instructions: %s", raw.get("strMeal"))
            return None

        # --- Build transformed recipe ---
        meal_id = raw.get("idMeal", "")
        transformed = {
            "id": f"mealdb-{meal_id}",
            "title": raw.get("strMeal", "Untitled"),
            "description": f"A {raw.get('strArea', 'Global')} dish from TheMealDB.",
            "ingredients": ingredients,
            "instructions": instructions,
            "tags": self._parse_tags(raw.get("strTags")),
            "cuisine": raw.get("strArea", "Global"),
            "source": "external",
            "image_url": raw.get("strMealThumb", ""),
        }

        # Validate against our schema
        if not self._validate_transformed(transformed):
            return None

        return transformed

    def _extract_ingredients(self, raw: dict) -> list[str]:
        """
        Collect strIngredient1..20 + strMeasure1..20 into a single list.

        Combines measure + ingredient into strings like "1 cup flour".
        Skips empty/whitespace-only entries.
        """
        ingredients = []
        for i in range(1, 21):
            ingredient = (raw.get(f"strIngredient{i}") or "").strip()
            measure = (raw.get(f"strMeasure{i}") or "").strip()

            if not ingredient:
                continue

            if measure:
                ingredients.append(f"{measure} {ingredient}")
            else:
                ingredients.append(ingredient)

        return ingredients

    def _parse_instructions(self, raw_instructions: str) -> list[str]:
        """
        Split a text block into individual instruction steps.

        TheMealDB instructions come as a single block of text.
        We split on:
        1. Numbered steps (e.g., "1.", "Step 1:", "STEP 1.")
        2. Line breaks (\\r\\n or \\n)
        """
        if not raw_instructions or not raw_instructions.strip():
            return []

        text = raw_instructions.strip()

        # Try splitting on numbered step patterns first: "1.", "1)", "Step 1:", etc.
        numbered_pattern = re.compile(r"(?:^|\n)\s*(?:step\s*)?\d+[.):\s]+", re.IGNORECASE)
        if numbered_pattern.search(text):
            # Split on the number patterns
            parts = numbered_pattern.split(text)
            steps = [step.strip() for step in parts if step.strip()]
            if len(steps) > 1:
                return steps

        # Fall back to splitting on line breaks
        lines = re.split(r"\r?\n", text)
        steps = [line.strip() for line in lines if line.strip()]
        return steps

    def _parse_tags(self, raw_tags: Optional[str]) -> list[str]:
        """Parse TheMealDB comma-separated tags string into a list."""
        if not raw_tags:
            return []
        return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]

    def _validate_transformed(self, data: dict) -> bool:
        """Validate a transformed recipe against our JSON Schema."""
        try:
            validate_recipe(data)
            return True
        except JsonSchemaValidationError as exc:
            logger.warning(
                "Transformed meal failed schema validation: %s — %s",
                data.get("title", "Unknown"),
                exc.message,
            )
            return False
