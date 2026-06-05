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
  X,
  Heart,
  Star,
  Bookmark,
  User as UserIcon,
  LogOut,
  Settings,
  FolderOpen
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

  // User State
  const [currentUser, setCurrentUser] = useState(null);
  const [collections, setCollections] = useState([]);
  const [activeCollectionDetail, setActiveCollectionDetail] = useState(null);

  // Auth Modal State
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [authFields, setAuthFields] = useState({
    username: '',
    email: '',
    password: '',
    profile_name: ''
  });
  const [authError, setAuthError] = useState('');

  // Profile Modal State
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [profileFields, setProfileFields] = useState({
    profile_name: '',
    preferences: {}
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
  const [activeSource, setActiveSource] = useState('all'); // 'all', 'internal', 'external', 'favorites', 'collections'

  // Toast State
  const [toasts, setToasts] = useState([]);

  // CSRF Utility
  const getCsrfToken = () => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; csrf_token=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  };

  const securedFetch = async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { ...(options.headers || {}) };
    
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      const csrf = getCsrfToken();
      if (csrf) {
        headers['X-CSRF-Token'] = csrf;
      }
    }
    
    const res = await fetch(url, {
      ...options,
      headers
    });
    
    if (res.status === 401 && !url.includes('/api/auth/me')) {
      setCurrentUser(null);
      setCollections([]);
    }
    return res;
  };

  // Apply Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('recipe-explorer-theme', theme);
  }, [theme]);

  // Check Auth State on mount
  useEffect(() => {
    checkCurrentUser();
  }, []);

  // Fetch collections when user logs in
  useEffect(() => {
    if (currentUser) {
      fetchCollections();
    } else {
      setCollections([]);
    }
  }, [currentUser]);

  // Debounce Search Query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch Recipes on search change or source filter change
  useEffect(() => {
    if (activeSource !== 'collections' && activeSource !== 'favorites') {
      fetchRecipes(debouncedSearch);
    }
  }, [debouncedSearch, activeSource]);

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

  const checkCurrentUser = async () => {
    try {
      const response = await securedFetch('/api/auth/me');
      if (response.ok) {
        const data = await response.json();
        setCurrentUser(data);
        setProfileFields({
          profile_name: data.profile_name || '',
          preferences: data.preferences || {}
        });
      }
    } catch (err) {
      console.log("Session not initialized yet");
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await securedFetch('/api/collections');
      if (response.ok) {
        const data = await response.json();
        setCollections(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRecipes = async (query = '') => {
    setLoading(true);
    const start = performance.now();
    try {
      const url = query.trim() 
        ? `/api/recipes/search?q=${encodeURIComponent(query.trim())}`
        : `/api/recipes/search`;
      
      const response = await securedFetch(url);
      if (!response.ok) throw new Error("Search failed");
      
      const data = await response.json();
      
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

  const fetchFavorites = async () => {
    setLoading(true);
    try {
      const response = await securedFetch('/api/favorites');
      if (!response.ok) throw new Error("Failed to fetch favorites");
      const data = await response.json();
      // Map favorite recipes to include source tags
      const mapped = data.map(r => ({ ...r, source: 'internal', is_favorite: true }));
      setRecipes(mapped);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchCollectionDetail = async (collectionId) => {
    setLoading(true);
    try {
      const response = await securedFetch(`/api/collections/${collectionId}`);
      if (!response.ok) throw new Error("Failed to load collection details");
      const data = await response.json();
      setActiveCollectionDetail(data);
      // Map recipes inside collection
      const mapped = (data.recipes || []).map(r => ({ ...r, source: 'internal' }));
      setRecipes(mapped);
    } catch (err) {
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchInternalCount = async () => {
    try {
      const response = await securedFetch('/api/recipes');
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
      const response = await securedFetch(`/api/recipes/external/${mealId}/save`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (!response.ok) throw new Error(data.detail || "Failed to save recipe");
      
      addToast(data.message || "Recipe saved to your database!");
      
      fetchRecipes(debouncedSearch);
      fetchInternalCount();
      
      if (selectedRecipe && selectedRecipe.id === mealId) {
        setSelectedRecipe(prev => ({ ...prev, source: 'internal' }));
      }
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleCreateOrUpdate = async (payload) => {
    try {
      const url = editingRecipe ? `/api/recipes/${editingRecipe.id}` : '/api/recipes';
      const method = editingRecipe ? 'PUT' : 'POST';
      
      const response = await securedFetch(url, {
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
      const response = await securedFetch(`/api/recipes/${recipeId}`, {
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

  const handleToggleFavorite = async (recipe) => {
    if (!currentUser) {
      setAuthMode('login');
      setIsAuthModalOpen(true);
      addToast("Please register or log in to favorite recipes", "info");
      return;
    }

    let recipeId = recipe.id;

    // Auto-save external recipe to local db if they click favorite
    if (recipe.source === 'external') {
      try {
        const saveRes = await securedFetch(`/api/recipes/external/${recipe.id}/save`, { method: 'POST' });
        const saveData = await saveRes.json();
        if (!saveRes.ok) throw new Error(saveData.detail || "Failed to save external recipe");
        recipeId = recipe.id;
        fetchRecipes(debouncedSearch);
        fetchInternalCount();
      } catch (err) {
        addToast(err.message, "error");
        return;
      }
    }

    const isFav = recipe.is_favorite;
    const url = `/api/favorites/${recipeId}`;
    const method = isFav ? 'DELETE' : 'POST';

    try {
      const response = await securedFetch(url, { method });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Favorite action failed");

      addToast(isFav ? "Removed from favorites" : "Added to favorites");

      // Update grid/detail states
      setRecipes(prev => prev.map(r => r.id === recipe.id ? { ...r, is_favorite: !isFav } : r));
      if (selectedRecipe && selectedRecipe.id === recipe.id) {
        setSelectedRecipe(prev => ({ ...prev, is_favorite: !isFav }));
      }

      if (activeSource === 'favorites') {
        fetchFavorites();
      }
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleRateRecipe = async (recipeId, score) => {
    if (!currentUser) {
      setAuthMode('login');
      setIsAuthModalOpen(true);
      addToast("Please log in to rate recipes", "info");
      return;
    }

    const targetRecipe = recipes.find(r => r.id === recipeId) || selectedRecipe;
    if (targetRecipe && targetRecipe.source === 'external') {
      try {
        const saveRes = await securedFetch(`/api/recipes/external/${recipeId}/save`, { method: 'POST' });
        if (!saveRes.ok) throw new Error("Failed to save recipe for rating");
        fetchRecipes(debouncedSearch);
        fetchInternalCount();
      } catch (err) {
        addToast(err.message, "error");
        return;
      }
    }

    try {
      const response = await securedFetch(`/api/recipes/${recipeId}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: score })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to rate recipe");

      addToast("Thank you for your rating!");
      fetchRecipes(debouncedSearch);

      if (selectedRecipe && selectedRecipe.id === recipeId) {
        setSelectedRecipe(prev => ({
          ...prev,
          user_rating: score,
          average_rating: data.average,
          rating_count: data.count
        }));
      }
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleAddRecipeToCollection = async (recipeId, collectionId, newColName) => {
    if (!currentUser) return;
    
    let targetCollectionId = collectionId;

    try {
      if (newColName) {
        const createRes = await securedFetch('/api/collections', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newColName })
        });
        const createData = await createRes.json();
        if (!createRes.ok) throw new Error(createData.detail || "Failed to create collection");
        targetCollectionId = createData.id;
        fetchCollections();
        addToast(`Created collection "${newColName}"`);
      }

      const res = await securedFetch(`/api/collections/${targetCollectionId}/recipes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipe_id: recipeId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to add recipe to collection");

      addToast("Recipe added to collection successfully");
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const payload = authMode === 'login' 
      ? { username: authFields.username, password: authFields.password }
      : authFields;

    try {
      const response = await securedFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Authentication failed");

      setCurrentUser(data);
      setProfileFields({
        profile_name: data.profile_name || '',
        preferences: data.preferences || {}
      });
      setIsAuthModalOpen(false);
      setAuthFields({ username: '', email: '', password: '', profile_name: '' });
      addToast(authMode === 'login' ? `Welcome back, ${data.profile_name}!` : "Registration successful!");
      
      // Reset filter sources
      setActiveSource('all');
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleLogout = async () => {
    try {
      await securedFetch('/api/auth/logout', { method: 'POST' });
      setCurrentUser(null);
      setCollections([]);
      setActiveCollectionDetail(null);
      setActiveSource('all');
      addToast("Successfully logged out");
    } catch (err) {
      console.error(err);
    }
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    try {
      const response = await securedFetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileFields)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to update profile");

      setCurrentUser(data);
      setIsProfileOpen(false);
      addToast("Profile updated successfully!");
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleDeleteCollection = async (e, colId) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this collection?")) {
      try {
        const response = await securedFetch(`/api/collections/${colId}`, { method: 'DELETE' });
        if (response.ok) {
          addToast("Collection deleted successfully");
          fetchCollections();
          if (activeCollectionDetail && activeCollectionDetail.id === colId) {
            setActiveCollectionDetail(null);
            setActiveSource('collections');
          }
        }
      } catch (err) {
        addToast("Failed to delete collection", "error");
      }
    }
  };

  const handleImportSuccess = () => {
    addToast("Collection imported successfully!");
    fetchRecipes(debouncedSearch);
    fetchInternalCount();
    setIsImportOpen(false);
  };

  // Cuisines list
  const cuisines = ['All', ...new Set(recipes
    .map(r => r.cuisine)
    .filter(c => c && c.trim().length > 0)
  )].slice(0, 10);

  // Apply filters
  const filteredRecipes = recipes.filter(recipe => {
    const matchesCuisine = activeCuisine === 'All' || recipe.cuisine === activeCuisine;
    const matchesSource = activeSource === 'all' 
      || (activeSource === 'internal' && recipe.source === 'internal')
      || (activeSource === 'external' && recipe.source === 'external')
      || activeSource === 'favorites'
      || activeSource === 'collections';
    return matchesCuisine && matchesSource;
  });

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-inner">
          <div className="brand" onClick={() => { setSearchQuery(''); setActiveCuisine('All'); setActiveSource('all'); setActiveCollectionDetail(null); }}>
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

            {/* Auth Dropdown or Button */}
            {currentUser ? (
              <div className="user-dropdown-container">
                <button className="btn btn-secondary user-dropdown-btn">
                  <UserIcon size={16} /> {currentUser.profile_name}
                </button>
                <div className="dropdown-menu">
                  <button className="dropdown-item" onClick={() => setIsProfileOpen(true)}>
                    <Settings size={14} /> My Profile
                  </button>
                  <button className="dropdown-item text-danger" onClick={handleLogout}>
                    <LogOut size={14} /> Logout
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn btn-primary" onClick={() => { setAuthMode('login'); setIsAuthModalOpen(true); }}>
                Log In
              </button>
            )}

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

          <div className="filter-source-tabs" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button 
              className={`filter-tab ${activeSource === 'all' ? 'active' : ''}`}
              onClick={() => { setActiveSource('all'); setActiveCollectionDetail(null); }}
            >
              All Sources
            </button>
            <button 
              className={`filter-tab ${activeSource === 'internal' ? 'active' : ''}`}
              onClick={() => { setActiveSource('internal'); setActiveCollectionDetail(null); }}
            >
              Database
            </button>
            <button 
              className={`filter-tab ${activeSource === 'external' ? 'active' : ''}`}
              onClick={() => { setActiveSource('external'); setActiveCollectionDetail(null); }}
            >
              TheMealDB
            </button>
            
            {/* Authenticated Filter Links */}
            {currentUser && (
              <>
                <button 
                  className={`filter-tab ${activeSource === 'favorites' ? 'active' : ''}`}
                  onClick={() => { setActiveSource('favorites'); setActiveCollectionDetail(null); fetchFavorites(); }}
                >
                  <Heart size={14} fill="currentColor" style={{ marginRight: '0.25rem' }} /> Favorites
                </button>
                <button 
                  className={`filter-tab ${activeSource === 'collections' ? 'active' : ''}`}
                  onClick={() => { setActiveSource('collections'); setActiveCollectionDetail(null); fetchCollections(); }}
                >
                  <Bookmark size={14} fill="currentColor" style={{ marginRight: '0.25rem' }} /> Collections
                </button>
              </>
            )}
          </div>
        </div>

        {/* Cuisine Filter Pills */}
        {activeSource !== 'collections' && (
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
        )}

        {/* Collections Viewer Page */}
        {activeSource === 'collections' && !activeCollectionDetail && (
          <div style={{ marginBottom: '2rem' }}>
            <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FolderOpen size={24} style={{ color: 'var(--color-primary)' }} /> My Collections
            </h2>
            {collections.length > 0 ? (
              <div className="collections-grid">
                {collections.map(col => (
                  <div key={col.id} className="collection-card" onClick={() => fetchCollectionDetail(col.id)}>
                    <div className="collection-card-icon">📁</div>
                    <div className="collection-card-body">
                      <h3 className="collection-card-title">{col.name}</h3>
                      <p className="collection-card-desc">{col.description || 'Personal recipes list.'}</p>
                    </div>
                    <button 
                      className="collection-delete-btn" 
                      onClick={(e) => handleDeleteCollection(e, col.id)}
                      aria-label="Delete Collection"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Bookmark size={48} className="empty-state-icon" />
                <h3 className="empty-state-title">No Collections Yet</h3>
                <p className="empty-state-desc">Organize your favorite recipes into custom collections. Add them from any recipe details page!</p>
              </div>
            )}
          </div>
        )}

        {/* Active Collection detail back banner */}
        {activeSource === 'collections' && activeCollectionDetail && (
          <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => { setActiveCollectionDetail(null); fetchCollections(); }}
            >
              ← Back to Collections
            </button>
            <div>
              <h2 style={{ fontSize: '1.5rem' }}>Collection: {activeCollectionDetail.name}</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{activeCollectionDetail.description || 'Custom collection.'}</p>
            </div>
          </div>
        )}

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
                onToggleFavorite={handleToggleFavorite}
              />
            ))}
          </div>
        ) : (
          !(activeSource === 'collections' && !activeCollectionDetail) && (
            <div className="empty-state">
              <ChefHat size={64} className="empty-state-icon" />
              <h3 className="empty-state-title">No Recipes Found</h3>
              <p className="empty-state-desc">
                We couldn't find any recipes matching your criteria. Try searching for something else like "chicken", "pasta", or add a custom recipe.
              </p>
              <button 
                className="btn btn-primary" 
                onClick={() => { setSearchQuery(''); setActiveCuisine('All'); setActiveSource('all'); setActiveCollectionDetail(null); }}
              >
                Reset Filters
              </button>
            </div>
          )
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
          onToggleFavorite={handleToggleFavorite}
          onRateRecipe={handleRateRecipe}
          collections={collections}
          onAddRecipeToCollection={handleAddRecipeToCollection}
          currentUser={currentUser}
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

      {/* Auth Modal Dialog */}
      {isAuthModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsAuthModalOpen(false)}>
          <div className="modal-content-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h3>
              <button className="modal-close-btn" onClick={() => setIsAuthModalOpen(false)}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleAuthSubmit} style={{ marginTop: '1rem' }}>
              {authError && <div className="auth-error-banner">{authError}</div>}
              
              <div className="form-group">
                <label>Username</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required
                  value={authFields.username}
                  onChange={(e) => setAuthFields(prev => ({ ...prev, username: e.target.value }))}
                />
              </div>

              {authMode === 'register' && (
                <>
                  <div className="form-group">
                    <label>Email Address</label>
                    <input 
                      type="email" 
                      className="form-input" 
                      required
                      value={authFields.email}
                      onChange={(e) => setAuthFields(prev => ({ ...prev, email: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Display Name</label>
                    <input 
                      type="text" 
                      className="form-input" 
                      value={authFields.profile_name}
                      placeholder="e.g. Master Chef"
                      onChange={(e) => setAuthFields(prev => ({ ...prev, profile_name: e.target.value }))}
                    />
                  </div>
                </>
              )}

              <div className="form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  className="form-input" 
                  required
                  value={authFields.password}
                  onChange={(e) => setAuthFields(prev => ({ ...prev, password: e.target.value }))}
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1.5rem' }}>
                {authMode === 'login' ? 'Log In' : 'Sign Up'}
              </button>
            </form>

            <div className="auth-toggle-hint">
              {authMode === 'login' ? (
                <span>New here? <button className="auth-link" onClick={() => { setAuthMode('register'); setAuthError(''); }}>Create an account</button></span>
              ) : (
                <span>Already have an account? <button className="auth-link" onClick={() => { setAuthMode('login'); setAuthError(''); }}>Log in</button></span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Profile/Preferences Modal */}
      {isProfileOpen && (
        <div className="modal-backdrop" onClick={() => setIsProfileOpen(false)}>
          <div className="modal-content-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Profile Settings</h3>
              <button className="modal-close-btn" onClick={() => setIsProfileOpen(false)}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleProfileUpdate} style={{ marginTop: '1.5rem' }}>
              <div className="form-group">
                <label>Display Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required
                  value={profileFields.profile_name}
                  onChange={(e) => setProfileFields(prev => ({ ...prev, profile_name: e.target.value }))}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1.5rem' }}>
                Save Profile
              </button>
            </form>
          </div>
        </div>
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
