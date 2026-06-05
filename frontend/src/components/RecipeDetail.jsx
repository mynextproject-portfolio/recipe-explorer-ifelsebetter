import React, { useState } from 'react';
import { X, Plus, Edit, Trash2, Globe, Heart, Star, Bookmark } from 'lucide-react';

const FALLBACK_GRADIENTS = [
  'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)',
  'linear-gradient(135deg, #4E54C8 0%, #8F94FB 100%)',
  'linear-gradient(135deg, #11998E 0%, #38EF7D 100%)',
  'linear-gradient(135deg, #FC466B 0%, #3F5EFB 100%)',
  'linear-gradient(135deg, #FF9966 0%, #FF5E62 100%)',
];

const FOOD_EMOJIS = ['🍳', '🥗', '🍲', '🍜', '🍝', '🍕', '🍰', '🌮', '🍔', '🍛'];

export default function RecipeDetail({ 
  recipe, 
  onClose, 
  onSaveExternal, 
  onEdit, 
  onDelete,
  onToggleFavorite,
  onRateRecipe,
  collections = [],
  onAddRecipeToCollection,
  currentUser
}) {
  const [checkedIngredients, setCheckedIngredients] = useState({});
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [hoverRating, setHoverRating] = useState(0);
  const [selectedCollectionId, setSelectedCollectionId] = useState('');
  const [newCollectionName, setNewCollectionName] = useState('');
  const [showNewCollectionInput, setShowNewCollectionInput] = useState(false);

  if (!recipe) return null;

  const isInternal = recipe.source === 'internal';

  // Fallback image helper
  const hash = (recipe.id || recipe.title || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const gradient = FALLBACK_GRADIENTS[hash % FALLBACK_GRADIENTS.length];
  const emoji = FOOD_EMOJIS[hash % FOOD_EMOJIS.length];

  const handleCheckboxChange = (index) => {
    setCheckedIngredients(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSaveExternal(recipe.id);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete "${recipe.title}"?`)) {
      setDeleting(true);
      try {
        await onDelete(recipe.id);
      } finally {
        setDeleting(false);
      }
    }
  };

  // Convert raw text instructions to array if it is a single string
  const getInstructionsArray = () => {
    if (Array.isArray(recipe.instructions)) {
      return recipe.instructions;
    }
    if (typeof recipe.instructions === 'string') {
      return recipe.instructions
        .split('\n')
        .map(step => step.trim())
        .filter(step => step.length > 0);
    }
    return [];
  };

  const instructions = getInstructionsArray();
  const ingredients = recipe.ingredients || [];

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <span className={`badge ${isInternal ? 'badge-source-internal' : 'badge-source-external'}`} style={{ marginBottom: '0.5rem', display: 'inline-block' }}>
              {isInternal ? 'Database' : 'TheMealDB'}
            </span>
            <h2 style={{ fontSize: '1.5rem' }}>{recipe.title}</h2>
          </div>
          <button className="drawer-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="drawer-content">
          {recipe.image_url ? (
            <img 
              src={recipe.image_url} 
              alt={recipe.title} 
              className="detail-img"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.parentNode.querySelector('.detail-placeholder').style.display = 'flex';
              }}
            />
          ) : null}

          <div 
            className="detail-placeholder" 
            style={{ 
              display: recipe.image_url ? 'none' : 'flex',
              width: '100%',
              height: '320px',
              background: gradient,
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '6.5rem',
              color: 'white',
              borderRadius: 'var(--radius-md)',
              marginBottom: '1.5rem',
              userSelect: 'none'
            }}
          >
            {emoji}
          </div>

          <div className="detail-meta-row">
            {recipe.cuisine && (
              <span className="detail-cuisine-badge">
                {recipe.cuisine}
              </span>
            )}
            {recipe.tags && recipe.tags.map((tag, idx) => (
              <span key={idx} className="tag-pill" style={{ fontSize: '0.85rem', padding: '0.25rem 0.75rem' }}>
                {tag}
              </span>
            ))}
          </div>

          <p className="detail-description">
            {recipe.description || 'No description provided.'}
          </p>

          {/* Interactive Star Rating Widget */}
          <div className="rating-widget-card">
            <span className="rating-widget-title">Recipe Rating</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              <div className="stars-row">
                {[1, 2, 3, 4, 5].map(star => (
                  <button
                    key={star}
                    className="star-button"
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                    onClick={() => onRateRecipe(recipe.id, star)}
                    aria-label={`Rate ${star} Stars`}
                  >
                    <Star 
                      size={24} 
                      className="star-icon"
                      fill={star <= (hoverRating || recipe.user_rating || 0) ? 'gold' : 'none'} 
                      stroke={star <= (hoverRating || recipe.user_rating || 0) ? 'gold' : 'var(--text-muted)'} 
                    />
                  </button>
                ))}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {recipe.average_rating > 0 ? (
                  <span>
                    Average: <strong>{recipe.average_rating}</strong> / 5.0 ({recipe.rating_count} {recipe.rating_count === 1 ? 'rating' : 'ratings'})
                  </span>
                ) : (
                  <span>No ratings yet. Be the first to rate!</span>
                )}
                {recipe.user_rating && (
                  <span style={{ display: 'block', color: 'var(--color-primary)', fontWeight: '600', fontSize: '0.75rem' }}>
                    You rated: {recipe.user_rating} ⭐
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Personal Collections Section */}
          <div className="collections-widget-card">
            <span className="rating-widget-title" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Bookmark size={16} /> Collections
            </span>
            <div style={{ marginTop: '0.5rem' }}>
              {isInternal ? (
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {showNewCollectionInput ? (
                    <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
                      <input 
                        type="text" 
                        placeholder="New collection name..." 
                        className="collection-input-field" 
                        value={newCollectionName} 
                        onChange={(e) => setNewCollectionName(e.target.value)}
                        onKeyDown={async (e) => {
                          if (e.key === 'Enter' && newCollectionName.trim()) {
                            await onAddRecipeToCollection(recipe.id, null, newCollectionName.trim());
                            setNewCollectionName('');
                            setShowNewCollectionInput(false);
                          }
                        }}
                      />
                      <button 
                        className="btn btn-primary" 
                        style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)' }}
                        onClick={async () => {
                          if (newCollectionName.trim()) {
                            await onAddRecipeToCollection(recipe.id, null, newCollectionName.trim());
                            setNewCollectionName('');
                            setShowNewCollectionInput(false);
                          }
                        }}
                      >
                        Create
                      </button>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-sm)' }}
                        onClick={() => setShowNewCollectionInput(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', width: '100%' }}>
                      <select 
                        className="collection-dropdown-select" 
                        value={selectedCollectionId}
                        onChange={async (e) => {
                          const val = e.target.value;
                          if (val === 'NEW') {
                            setShowNewCollectionInput(true);
                          } else if (val) {
                            await onAddRecipeToCollection(recipe.id, val);
                            setSelectedCollectionId('');
                          }
                        }}
                      >
                        <option value="">Add to a collection...</option>
                        {collections.map(col => (
                          <option key={col.id} value={col.id}>{col.name}</option>
                        ))}
                        <option value="NEW">+ Create New Collection...</option>
                      </select>
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Save this recipe to your database to organize it into collections.
                </p>
              )}
            </div>
          </div>

          <h3 className="detail-section-title">Ingredients Checklist</h3>
          {ingredients.length > 0 ? (
            <div className="ingredient-list">
              {ingredients.map((ingredient, idx) => (
                <label key={idx} className="ingredient-item">
                  <input 
                    type="checkbox" 
                    className="ingredient-checkbox"
                    checked={!!checkedIngredients[idx]}
                    onChange={() => handleCheckboxChange(idx)}
                  />
                  <span className="ingredient-text">{ingredient}</span>
                </label>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>No ingredients listed.</p>
          )}

          <h3 className="detail-section-title">Instructions</h3>
          {instructions.length > 0 ? (
            <div className="step-list">
              {instructions.map((step, idx) => (
                <div key={idx} className="step-item">
                  <div className="step-number">{idx + 1}</div>
                  <div className="step-text">{step}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)' }}>No instructions listed.</p>
          )}
        </div>

        <div className="drawer-footer">
          {/* Favorite heart toggle button */}
          <button 
            className={`btn ${recipe.is_favorite ? 'btn-danger' : 'btn-secondary'}`}
            onClick={() => onToggleFavorite(recipe)}
          >
            <Heart size={16} fill={recipe.is_favorite ? 'white' : 'none'} />
            {recipe.is_favorite ? 'Favorited' : 'Favorite'}
          </button>

          {isInternal ? (
            <>
              <button 
                className="btn btn-secondary" 
                onClick={() => {
                  onEdit(recipe);
                }}
              >
                <Edit size={16} /> Edit
              </button>
              <button 
                className="btn btn-danger" 
                onClick={handleDelete}
                disabled={deleting}
              >
                <Trash2 size={16} /> {deleting ? 'Deleting...' : 'Delete'}
              </button>
            </>
          ) : (
            <button 
              className="btn btn-primary" 
              onClick={handleSave}
              disabled={saving}
            >
              <Plus size={16} /> 
              {saving ? 'Saving...' : 'Save to Database'}
            </button>
          )}
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
