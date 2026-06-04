#!/usr/bin/env python3
import sys
import json
import os
from pydantic import ValidationError

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Recipe


def validate_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: File '{filepath}' is not valid JSON. Details: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: The root of the JSON file must be an array of recipes.")
        sys.exit(1)

    has_errors = False
    for i, item in enumerate(data):
        try:
            # We use the Recipe model to validate
            Recipe(**item)
        except ValidationError as e:
            has_errors = True
            print(f"\n--- Validation Error in Recipe at index {i} ---")
            title = item.get("title", "Unknown Title")
            print(f"Recipe Title: {title}")
            for error in e.errors():
                loc = " -> ".join([str(x) for x in error["loc"]])
                print(f"  Field: {loc}")
                print(f"  Error: {error['msg']}")
                print(f"  Type: {error['type']}")

    if has_errors:
        print("\nValidation failed. Please fix the errors above.")
        sys.exit(1)
    else:
        print(f"Validation successful. All {len(data)} recipes are compliant.")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.path) < 2 or len(sys.argv) < 2:
        print("Usage: python validate_recipes.py <path_to_json_file>")
        sys.exit(1)

    validate_file(sys.argv[1])
