import React from 'react';
import { Tag, BookOpen, Globe } from 'lucide-react';

const FALLBACK_GRADIENTS = [
  'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)',
  'linear-gradient(135deg, #4E54C8 0%, #8F94FB 100%)',
  'linear-gradient(135deg, #11998E 0%, #38EF7D 100%)',
  'linear-gradient(135deg, #FC466B 0%, #3F5EFB 100%)',
  'linear-gradient(135deg, #FF9966 0%, #FF5E62 100%)',
];

const FOOD_EMOJIS = ['🍳', '🥗', '🍲', '🍜', '🍝', '🍕', '🍰', '🌮', '🍔', '🍛'];

export default function RecipeCard({ recipe, onClick }) {
  const isInternal = recipe.source === 'internal';
  
  // Deterministic fallback based on recipe ID or title
  const hash = (recipe.id || recipe.title || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const gradient = FALLBACK_GRADIENTS[hash % FALLBACK_GRADIENTS.length];
  const emoji = FOOD_EMOJIS[hash % FOOD_EMOJIS.length];

  return (
    <div className="recipe-card" onClick={() => onClick(recipe)}>
      <div className="recipe-card-img-container">
        {recipe.image_url ? (
          <img 
            src={recipe.image_url} 
            alt={recipe.title} 
            className="recipe-card-img"
            loading="lazy"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.parentNode.querySelector('.recipe-placeholder').style.display = 'flex';
            }}
          />
        ) : null}
        
        <div 
          className="recipe-placeholder" 
          style={{ 
            display: recipe.image_url ? 'none' : 'flex',
            width: '100%',
            height: '100%',
            background: gradient,
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '4.5rem',
            color: 'white',
            userSelect: 'none'
          }}
        >
          {emoji}
        </div>

        <div className="recipe-card-badges">
          <span className={`badge ${isInternal ? 'badge-source-internal' : 'badge-source-external'}`}>
            {isInternal ? 'Database' : 'TheMealDB'}
          </span>
          {recipe.cuisine && (
            <span className="badge badge-cuisine">
              {recipe.cuisine}
            </span>
          )}
        </div>
      </div>

      <div className="recipe-card-content">
        <h3 className="recipe-card-title">{recipe.title}</h3>
        <p className="recipe-card-description">
          {recipe.description || 'A delicious recipe ready to cook.'}
        </p>
        
        <div className="recipe-card-footer">
          <div className="recipe-card-tags">
            {recipe.tags && recipe.tags.length > 0 ? (
              recipe.tags.slice(0, 3).map((tag, idx) => (
                <span key={idx} className="tag-pill">
                  {tag.toLowerCase()}
                </span>
              ))
            ) : (
              <span className="tag-pill">recipe</span>
            )}
          </div>
          <div className="recipe-card-meta">
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <BookOpen size={12} /> View Recipe
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
