import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Plus, 
  Database, 
  Sun, 
  Moon, 
  Trash2, 
  Edit, 
  BookOpen, 
  DownloadCloud, 
  ChefHat, 
  Sparkles,
  X 
} from 'lucide-react';

// Components
import DashboardStats from './components/DashboardStats';
import RecipeCard from './components/RecipeCard';
import RecipeDetail from './components/RecipeDetail';
import RecipeForm from './components/RecipeForm';
import ImportExport from './components/ImportExport';

export default function App() {
  // Theme State
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('recipe-explorer-theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  // Data States
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [internalCount, setInternalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [lastStats, setLastStats] = useState({
    cache: 'MISS',
    internalTime: 0,
    externalTime: 0,
    totalTime: 0
  });

  // Modal / Drawer States
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState(null);
  const [isImportOpen, setIsImportOpen] = useState(false);

  // Filter States
  const [activeCuisine, setActiveCuisine] = useState('All');
  const [activeSource, setActiveSource] = useState('all'); // 'all', 'internal', 'external'

  // Toast State
  const [toasts, setToasts] = useState([]);

  // Apply Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('recipe-explorer-theme', theme);
  }, [theme]);

  // Debounce Search Query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch Recipes and Stats on search change
  useEffect(() => {
    fetchRecipes(debouncedSearch);
  }, [debouncedSearch]);

  // Initial stats and counts
  useEffect(() => {
    fetchInternalCount();
  }, []);

  const addToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const fetchRecipes = async (query = '') => {
    setLoading(true);
    const start = performance.now();
    try {
      // We call the unified search endpoint
      const url = query.trim() 
        ? `/api/recipes/search?q=${encodeURIComponent(query.trim())}`
        : `/api/recipes/search`;
      
      const response = await fetch(url);
      if (!response.ok) throw new Error("Search failed");
      
      const data = await response.json();
      
      // Parse custom response headers
      const cache = response.headers.get('X-Cache') || 'MISS';
      const internalTime = parseFloat(response.headers.get('X-Internal-Time-Ms') || '0');
      const externalTime = parseFloat(response.headers.get('X-External-Time-Ms') || '0');
      const totalTime = performance.now() - start;

      setRecipes(data);
      setLastStats({
        cache,
        internalTime,
        externalTime,
        totalTime
      });
    } catch (err) {
      console.error(err);
      addToast("Failed to fetch recipes", "error");
    } finally {
      setLoading(false);
    }
  };

  const fetchInternalCount = async () => {
    try {
      const response = await fetch('/api/recipes');
      if (response.ok) {
        const data = await response.json();
        setInternalCount(data.recipes ? data.recipes.length : 0);
      }
    } catch (err) {
      console.error("Failed to fetch internal count", err);
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleSaveExternal = async (mealId) => {
    try {
      const response = await fetch(`/api/recipes/external/${mealId}/save`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || "Failed to save recipe");
      
      addToast(data.message || "Recipe saved to your database!");
      
      // Refresh list & database count
      fetchRecipes(debouncedSearch);
      fetchInternalCount();
      
      // Update the active drawer view to internal since it has been saved
      if (selectedRecipe && selectedRecipe.id === mealId) {
        const savedRecipe = { ...selectedRecipe, source: 'internal' };
        setSelectedRecipe(savedRecipe);
      }
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleCreateOrUpdate = async (payload) => {
    try {
      const url = editingRecipe ? `/api/recipes/${editingRecipe.id}` : '/api/recipes';
      const method = editingRecipe ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Action failed");

      addToast(editingRecipe ? "Recipe updated successfully!" : "Recipe created successfully!");
      setIsFormOpen(false);
      setEditingRecipe(null);
      
      fetchRecipes(debouncedSearch);
      fetchInternalCount();
      
      // If we edited the currently open recipe detail, update the detail view
      if (selectedRecipe && editingRecipe && selectedRecipe.id === editingRecipe.id) {
        setSelectedRecipe({ ...data, source: 'internal' });
      }
    } catch (err) {
      addToast(err.message, "error");
      throw err;
    }
  };

  const handleDelete = async (recipeId) => {
    try {
      const response = await fetch(`/api/recipes/${recipeId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || "Delete failed");
      
      addToast("Recipe deleted successfully");
      setSelectedRecipe(null);
      
      fetchRecipes(debouncedSearch);
      fetchInternalCount();
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleImportSuccess = () => {
    addToast("Collection imported successfully!");
    fetchRecipes(debouncedSearch);
    fetchInternalCount();
    setIsImportOpen(false);
  };

  // Extract Cuisines dynamically
  const cuisines = ['All', ...new Set(recipes
    .map(r => r.cuisine)
    .filter(c => c && c.trim().length > 0)
  )].slice(0, 10);

  // Apply filters
  const filteredRecipes = recipes.filter(recipe => {
    const matchesCuisine = activeCuisine === 'All' || recipe.cuisine === activeCuisine;
    const matchesSource = activeSource === 'all' 
      || (activeSource === 'internal' && recipe.source === 'internal')
      || (activeSource === 'external' && recipe.source === 'external');
    return matchesCuisine && matchesSource;
  });

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="brand" onClick={() => { setSearchQuery(''); setActiveCuisine('All'); setActiveSource('all'); }}>
            <ChefHat size={32} style={{ color: 'var(--color-primary)' }} />
            <span>Recipe Explorer</span>
          </div>

          <div className="nav-actions">
            <button className="btn btn-secondary" onClick={() => setIsImportOpen(true)}>
              <DownloadCloud size={16} /> Backup/Import
            </button>
            <button className="btn btn-primary" onClick={() => { setEditingRecipe(null); setIsFormOpen(true); }}>
              <Plus size={16} /> Add Recipe
            </button>
            <button className="theme-switch-btn" onClick={toggleTheme} aria-label="Toggle Theme">
              {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Live Performance Panel */}
        <DashboardStats stats={lastStats} recipeCount={internalCount} />

        {/* Controls and Search */}
        <div className="controls-row">
          <div className="search-container">
            <input 
              type="text" 
              className="search-input"
              placeholder="Search recipes, ingredients, or cuisines..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search className="search-icon" size={20} />
            {searchQuery && (
              <button className="search-clear" onClick={() => setSearchQuery('')}>
                <X size={16} />
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className={`filter-tab ${activeSource === 'all' ? 'active' : ''}`}
              onClick={() => setActiveSource('all')}
            >
              All Sources
            </button>
            <button 
              className={`filter-tab ${activeSource === 'internal' ? 'active' : ''}`}
              onClick={() => setActiveSource('internal')}
            >
              Database
            </button>
            <button 
              className={`filter-tab ${activeSource === 'external' ? 'active' : ''}`}
              onClick={() => setActiveSource('external')}
            >
              TheMealDB
            </button>
          </div>
        </div>

        {/* Cuisine Filter Pills */}
        <div style={{ marginBottom: '2rem' }}>
          <div className="filter-tabs">
            {cuisines.map(cuisine => (
              <button
                key={cuisine}
                className={`filter-tab ${activeCuisine === cuisine ? 'active' : ''}`}
                onClick={() => setActiveCuisine(cuisine)}
              >
                {cuisine}
              </button>
            ))}
          </div>
        </div>

        {/* Grid and States */}
        {loading ? (
          <div className="recipes-grid">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="skeleton-card">
                <div className="skeleton-img skeleton-shimmer"></div>
                <div className="skeleton-text-title skeleton-shimmer"></div>
                <div className="skeleton-text-desc skeleton-shimmer"></div>
              </div>
            ))}
          </div>
        ) : filteredRecipes.length > 0 ? (
          <div className="recipes-grid">
            {filteredRecipes.map(recipe => (
              <RecipeCard 
                key={recipe.id}
                recipe={recipe} 
                onClick={(rec) => setSelectedRecipe(rec)} 
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <ChefHat size={64} className="empty-state-icon" />
            <h3 className="empty-state-title">No Recipes Found</h3>
            <p className="empty-state-desc">
              We couldn't find any recipes matching your criteria. Try searching for something else like "chicken", "pasta", or add a custom recipe.
            </p>
            <button 
              className="btn btn-primary" 
              onClick={() => { setSearchQuery(''); setActiveCuisine('All'); setActiveSource('all'); }}
            >
              Reset Filters
            </button>
          </div>
        )}
      </main>

      {/* Side-Drawer Details View */}
      {selectedRecipe && (
        <RecipeDetail 
          recipe={selectedRecipe}
          onClose={() => setSelectedRecipe(null)}
          onSaveExternal={handleSaveExternal}
          onEdit={(rec) => {
            setEditingRecipe(rec);
            setIsFormOpen(true);
          }}
          onDelete={handleDelete}
        />
      )}

      {/* Recipe Form Dialog (New & Edit) */}
      {isFormOpen && (
        <RecipeForm 
          recipe={editingRecipe}
          onClose={() => { setIsFormOpen(false); setEditingRecipe(null); }}
          onSubmit={handleCreateOrUpdate}
        />
      )}

      {/* Import / Export Dialog */}
      {isImportOpen && (
        <ImportExport 
          onClose={() => setIsImportOpen(false)}
          onImportSuccess={handleImportSuccess}
        />
      )}

      {/* Toasts Container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
