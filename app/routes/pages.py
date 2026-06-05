from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

router = APIRouter()
INDEX_PATH = Path("frontend/dist/index.html")


def get_index_response():
    """Return the SPA index.html, or a fallback template if not compiled yet."""
    if INDEX_PATH.exists():
        return FileResponse(INDEX_PATH)

    # Clean fallback for local dev / tests when React is not yet compiled
    fallback_html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Recipe Explorer</title>
        <style>
          body {
            font-family: sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background-color: #f8f9fa;
            color: #212529;
          }
          .card {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Recipe Explorer</h1>
          <p>React application is initializing. If you see this, please run <code>npm run build</code> in the <code>frontend/</code> directory.</p>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=fallback_html, status_code=200)


@router.get("/", response_class=HTMLResponse)
async def home():
    """Home page routing to React SPA"""
    return get_index_response()


@router.get("/recipes/new", response_class=HTMLResponse)
def new_recipe_form():
    """New recipe routing to React SPA"""
    return get_index_response()


@router.get("/recipes/{recipe_id}", response_class=HTMLResponse)
def recipe_detail(recipe_id: str):
    """Recipe detail routing to React SPA"""
    return get_index_response()


@router.get("/recipes/{recipe_id}/edit", response_class=HTMLResponse)
def edit_recipe_form(recipe_id: str):
    """Edit recipe routing to React SPA"""
    return get_index_response()


@router.get("/import", response_class=HTMLResponse)
def import_page():
    """Import page routing to React SPA"""
    return get_index_response()
