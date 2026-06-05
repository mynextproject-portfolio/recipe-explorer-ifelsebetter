# API v2 Migration Guide

This document outlines the transition path, version negotiation, and schema changes for clients migrating from Recipe Explorer API v1 to API v2.

---

## 1. Versioning Strategy

Recipe Explorer supports two mechanisms for version selection:
1. **Explicit Path Prefix:** Route requests directly via `/api/v1/recipes` or `/api/v2/recipes`.
2. **Content Negotiation (Accept Header):** Query the base `/api/recipes` path and request a specific payload schema using the `Accept` HTTP header:
   - **V2 Schema:** `Accept: application/vnd.recipe.v2+json`
   - **V1 Schema (Default):** Returns V1 format if the header is absent or set to `application/json`.

---

## 2. Deprecation & Sunset Timeline

To ensure backward compatibility and smooth transitions, V1 endpoints are officially **Deprecated** and scheduled for **Sunset** on **December 31, 2026**.

All requests handled by V1 endpoints include the following standard RFC headers:
* `Deprecation: true` (indicates the resource is deprecated)
* `Sunset: Thu, 31 Dec 2026 23:59:59 GMT` (final shutdown time)
* `Link: </api/v2/migration>; rel="sunset"` (reference link to migration guide)

---

## 3. Recipe Schema Changes

### V1 vs V2 Payload Comparison

V2 expands the core Recipe structure to include nutritional, difficulty, equipment, techniques, and relationship details.

| Field Name | Type | Description | Changed/Added in V2 |
| :--- | :--- | :--- | :--- |
| `nutrition` | `object` | Optional calories, protein, fat, and carbs details. | **New** |
| `dietary_restrictions` | `array[string]` | E.g. `["vegan", "gluten-free"]`. | **New** |
| `difficulty` | `object` | Level (`easy`, `medium`, `hard`) and prep/cook durations. | **New** |
| `equipment` | `array[string]` | E.g. `["blender", "oven"]`. | **New** |
| `techniques` | `array[string]` | E.g. `["baking", "whipping"]`. | **New** |
| `relationships` | `object` | Ingredient substitutions and recipe variations. | **New** |

#### V2 Schema JSON Definition
```json
{
  "nutrition": {
    "calories": 350.0,
    "protein_g": 12.5,
    "fat_g": 10.0,
    "carbs_g": 45.0
  },
  "dietary_restrictions": ["vegetarian", "gluten-free"],
  "difficulty": {
    "level": "easy",
    "prep_time_minutes": 10,
    "cook_time_minutes": 20
  },
  "equipment": ["frying pan", "spatula"],
  "techniques": ["sauteing"],
  "relationships": {
    "substitutions": {
      "butter": "coconut oil"
    },
    "variations": ["another-recipe-uuid"]
  }
}
```

---

## 4. Bulk Operations

V2 introduces atomic bulk endpoints to optimize client synchronization workflows. All bulk operations run within single database transactions.

### Bulk Create
* **Method:** `POST`
* **URL:** `/api/v2/recipes/bulk`
* **Request Body:** `Array` of `RecipeV2Create`
* **Response:**
  ```json
  {
    "message": "Successfully created 2 recipes",
    "recipes": [...]
  }
  ```

### Bulk Update
* **Method:** `PUT`
* **URL:** `/api/v2/recipes/bulk`
* **Request Body:**
  ```json
  {
    "updates": [
      {
        "id": "recipe-uuid-1",
        "recipe": { ...RecipeV2Update... }
      }
    ]
  }
  ```

### Bulk Delete
* **Method:** `DELETE`
* **URL:** `/api/v2/recipes/bulk`
* **Request Body:**
  ```json
  {
    "ids": ["recipe-uuid-1", "recipe-uuid-2"]
  }
  ```
  *Note: If a client attempts to update or delete any recipe they do not own, the operation fails completely (atomic rollback).*

---

## 5. Migration Checklist

- [ ] Update client headers to append `Accept: application/vnd.recipe.v2+json` when querying `/api/recipes`.
- [ ] Migrate base URL prefixes to `/api/v2/recipes` for new feature deployments.
- [ ] Adapt client models to parse new nested fields (`nutrition`, `difficulty`, etc.).
- [ ] Leverage `/api/v2/recipes/bulk` to reduce network request overhead for synchronization.
