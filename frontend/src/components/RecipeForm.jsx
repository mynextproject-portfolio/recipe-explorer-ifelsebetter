import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save } from 'lucide-react';

export default function RecipeForm({ recipe, onClose, onSubmit }) {
  const isEdit = !!recipe;
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [tags, setTags] = useState('');
  const [ingredients, setIngredients] = useState(['']);
  const [instructions, setInstructions] = useState(['']);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (recipe) {
      setTitle(recipe.title || '');
      setDescription(recipe.description || '');
      setCuisine(recipe.cuisine || '');
      setTags(recipe.tags ? recipe.tags.join(', ') : '');
      setIngredients(recipe.ingredients && recipe.ingredients.length > 0 ? recipe.ingredients : ['']);
      
      let instArray = [''];
      if (Array.isArray(recipe.instructions)) {
        instArray = recipe.instructions;
      } else if (typeof recipe.instructions === 'string') {
        instArray = recipe.instructions.split('\n').filter(s => s.trim().length > 0);
      }
      setInstructions(instArray.length > 0 ? instArray : ['']);
    }
  }, [recipe]);

  const handleAddIngredient = () => {
    setIngredients([...ingredients, '']);
  };

  const handleRemoveIngredient = (index) => {
    const nextIng = [...ingredients];
    nextIng.splice(index, 1);
    setIngredients(nextIng.length > 0 ? nextIng : ['']);
  };

  const handleIngredientChange = (index, value) => {
    const nextIng = [...ingredients];
    nextIng[index] = value;
    setIngredients(nextIng);
  };

  const handleAddInstruction = () => {
    setInstructions([...instructions, '']);
  };

  const handleRemoveInstruction = (index) => {
    const nextInst = [...instructions];
    nextInst.splice(index, 1);
    setInstructions(nextInst.length > 0 ? nextInst : ['']);
  };

  const handleInstructionChange = (index, value) => {
    const nextInst = [...instructions];
    nextInst[index] = value;
    setInstructions(nextInst);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validations
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (title.length > 200) {
      setError('Title cannot exceed 200 characters');
      return;
    }
    if (!cuisine.trim()) {
      setError('Cuisine is required');
      return;
    }

    const filteredIngredients = ingredients.map(i => i.trim()).filter(i => i.length > 0);
    if (filteredIngredients.length === 0) {
      setError('At least one ingredient is required');
      return;
    }

    const filteredInstructions = instructions.map(i => i.trim()).filter(i => i.length > 0);
    if (filteredInstructions.length === 0) {
      setError('At least one instruction step is required');
      return;
    }

    const tagList = tags
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0);

    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        cuisine: cuisine.trim(),
        ingredients: filteredIngredients,
        instructions: filteredInstructions,
        tags: tagList
      };
      await onSubmit(payload);
    } catch (err) {
      setError(err.message || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>{isEdit ? 'Edit Recipe' : 'New Recipe'}</h2>
          <button className="drawer-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <div className="dialog-content">
            {error && (
              <div style={{ backgroundColor: 'var(--color-error-light)', color: 'var(--color-error)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', fontSize: '0.875rem', fontWeight: 600 }}>
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="title">Recipe Title *</label>
              <input 
                type="text" 
                id="title"
                className="form-control"
                placeholder="e.g., Spaghetti Carbonara"
                value={title}
                onChange={e => setTitle(e.target.value)}
                maxLength={200}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="description">Short Description</label>
              <textarea 
                id="description"
                className="form-control"
                placeholder="e.g., A classic Roman pasta dish made with eggs, hard cheese, cured pork, and black pepper."
                value={description}
                onChange={e => setDescription(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label className="form-label" htmlFor="cuisine">Cuisine *</label>
                <input 
                  type="text" 
                  id="cuisine"
                  className="form-control"
                  placeholder="e.g., Italian"
                  value={cuisine}
                  onChange={e => setCuisine(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="form-label" htmlFor="tags">Tags (comma-separated)</label>
                <input 
                  type="text" 
                  id="tags"
                  className="form-control"
                  placeholder="Pasta, Quick, Dinner"
                  value={tags}
                  onChange={e => setTags(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Ingredients *</label>
              {ingredients.map((ing, idx) => (
                <div key={idx} className="dynamic-list-row">
                  <input 
                    type="text" 
                    className="form-control"
                    placeholder={`Ingredient #${idx + 1}`}
                    value={ing}
                    onChange={e => handleIngredientChange(idx, e.target.value)}
                    required
                  />
                  <button 
                    type="button" 
                    className="btn-icon-only" 
                    style={{ height: '2.5rem', width: '2.5rem', border: 'none', backgroundColor: 'var(--bg-input)' }}
                    onClick={() => handleRemoveIngredient(idx)}
                    disabled={ingredients.length <= 1}
                  >
                    <Trash2 size={14} className="text-danger" />
                  </button>
                </div>
              ))}
              <button 
                type="button" 
                className="btn btn-secondary" 
                style={{ padding: '0.4rem 1rem', fontSize: '0.85rem', marginTop: '0.5rem' }}
                onClick={handleAddIngredient}
              >
                <Plus size={14} /> Add Ingredient
              </button>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Instructions (Step by Step) *</label>
              {instructions.map((inst, idx) => (
                <div key={idx} className="dynamic-list-row" style={{ alignItems: 'flex-start' }}>
                  <span style={{ minWidth: '1.5rem', marginTop: '0.5rem', fontWeight: 700, color: 'var(--text-muted)' }}>{idx + 1}.</span>
                  <textarea 
                    className="form-control"
                    placeholder={`Step #${idx + 1}`}
                    value={inst}
                    onChange={e => handleInstructionChange(idx, e.target.value)}
                    required
                  />
                  <button 
                    type="button" 
                    className="btn-icon-only" 
                    style={{ height: '2.5rem', width: '2.5rem', border: 'none', backgroundColor: 'var(--bg-input)', marginTop: '0.25rem' }}
                    onClick={() => handleRemoveInstruction(idx)}
                    disabled={instructions.length <= 1}
                  >
                    <Trash2 size={14} className="text-danger" />
                  </button>
                </div>
              ))}
              <button 
                type="button" 
                className="btn btn-secondary" 
                style={{ padding: '0.4rem 1rem', fontSize: '0.85rem', marginTop: '0.5rem' }}
                onClick={handleAddInstruction}
              >
                <Plus size={14} /> Add Step
              </button>
            </div>
          </div>

          <div className="dialog-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <Save size={16} /> {submitting ? 'Saving...' : 'Save Recipe'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
