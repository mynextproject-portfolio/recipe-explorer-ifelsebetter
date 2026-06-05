import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import api, pages
from app.routes import mealdb_routes, auth_routes, collection_routes, interaction_routes
from app.recipe_schema import get_schema
from app.services.mealdb_adapter import MealDBAdapter
from app.dependencies import get_storage
from prometheus_fastapi_instrumentator import Instrumentator

# App configuration
APP_NAME = "Recipe Explorer"
VERSION = "1.0.0"
DEBUG = True

SAMPLE_DATA_PATH = Path(__file__).parent.parent / "sample-recipes.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load sample recipes during application startup."""
    storage = get_storage()
    if not SAMPLE_DATA_PATH.exists():
        print(f"No sample data file found at {SAMPLE_DATA_PATH}")
    else:
        try:
            with open(SAMPLE_DATA_PATH, "r", encoding="utf-8") as sample_file:
                recipes_data = json.load(sample_file)
            count = storage.import_recipes(recipes_data)
            print(f"Seeded {count} recipes from {SAMPLE_DATA_PATH.name}")
        except Exception as error:
            print(f"Failed to seed sample data: {error}")

    # Initialize Redis cache and TheMealDB adapter
    from app.services.cache import RedisCache
    from app.dependencies import set_dependencies

    cache = RedisCache()
    set_dependencies(cache=cache, mealdb_adapter=MealDBAdapter(cache=cache))

    yield


# Create FastAPI app
app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount React frontend static assets if they exist
react_dist = Path("frontend/dist")
if react_dist.exists():
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Include routers
app.include_router(api.router)
app.include_router(mealdb_routes.router)
app.include_router(auth_routes.router)
app.include_router(collection_routes.router)
app.include_router(interaction_routes.router)
app.include_router(pages.router)


# Basic health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/schema")
def recipe_schema():
    """Return the canonical recipe JSON Schema (the API contract)."""
    return get_schema()


# Prometheus auto-instrumentation: registers middleware for HTTP request
# duration / count / in-progress metrics and exposes GET /metrics.
# TODO(security): In production, restrict /metrics to internal network only.
Instrumentator().instrument(app).expose(app)


# Serve root static assets from frontend/dist (e.g., vite.svg, favicon.ico)
@app.get("/{file_name}")
def serve_root_file(file_name: str):
    file_path = Path("frontend/dist") / file_name
    if file_path.exists() and file_path.is_file():
        from fastapi.responses import FileResponse
        return FileResponse(file_path)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Not found")



# @app.get("/status")
# def status():
#     return {"status": "ok", "version": "1.0.0"}
