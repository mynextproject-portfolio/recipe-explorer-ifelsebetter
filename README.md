# Recipe Explorer

A simple FastAPI web application for managing recipes. Features CRUD operations, search, file uploads, and a Bootstrap frontend.

**Tech Stack:** FastAPI, Jinja2, Bootstrap 5, pytest

## Quick Start

### Run Locally

```bash
# Clone and setup
git clone <repository-url>
cd <your-repo-name>
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install and run
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit **http://localhost:8000**

### Run with Docker (optional)

```bash
docker build -t recipe-explorer .
docker run -p 8000:8000 recipe-explorer
```

Visit **http://localhost:8000**

## Sample Data

The server automatically loads 3 example recipes from `sample-recipes.json` on startup — no manual upload needed. Edit this file and restart the server to see your changes.

## Testing

```bash
pytest           # Run all tests
pytest -v        # Verbose output
```

## API Endpoints

**Pages:**
- `/` - Home page with recipe list
- `/recipes/new` - Add recipe form  
- `/recipes/{id}` - Recipe detail page
- `/import` - Import recipes

**API:**
- `GET /api/recipes` - List/search recipes
- `POST /api/recipes` - Create recipe
- `GET /api/recipes/{id}` - Get recipe
- `PUT /api/recipes/{id}` - Update recipe
- `DELETE /api/recipes/{id}` - Delete recipe
- `POST /api/recipes/import` - Import JSON
- `GET /api/recipes/export` - Export JSON

---

> **Tip:** If you run into any issues, use your AI assistant — it can help you debug errors, understand the code, and get unstuck quickly.

*Part of [mynextproject.dev](https://mynextproject.dev) - Learn to code like a professional*
