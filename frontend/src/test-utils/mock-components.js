// src/test-utils/mock-components.js
import React, { useState } from 'react';

// Mock Relationship Form Component
export const MockRelationshipForm = ({ 
  initialData = {},
  onSubmit,
  onCancel
}) => {
  const [formData, setFormData] = useState(initialData);
  
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };
  
  return (
    <div className="relationship-form" data-testid="relationship-form">
      <h2>Relationship Details</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="type">Relationship Type</label>
          <select 
            data-testid="relationship-type"
            id="type" 
            name="type" 
            value={formData.type || ''}
            onChange={handleChange}
          >
            <option value="">Select type</option>
            <option value="spouse_current">Spouse (Current)</option>
            <option value="biological_parent">Biological Parent</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="description">Description</label>
          <input 
            data-testid="relationship-description"
            type="text" 
            id="description" 
            name="description" 
            value={formData.description || ''}
            onChange={handleChange}
          />
        </div>
        
        <div className="buttons">
          <button 
            type="submit" 
            data-testid="submit-button"
          >
            Save
          </button>
          <button 
            type="button" 
            onClick={onCancel}
            data-testid="cancel-button"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

// Mock Relationship Timeline Component
export const MockRelationshipTimeline = ({ 
  relationships = [],
  onEdit,
  onDelete
}) => {
  return (
    <div className="relationship-timeline" data-testid="relationship-timeline">
      <h2>Relationships</h2>
      {relationships.length === 0 ? (
        <p data-testid="no-relationships">No relationships found</p>
      ) : (
        <ul>
          {relationships.map((relationship) => (
            <li key={relationship.id} data-testid={`relationship-${relationship.id}`}>
              <div className="relationship-card">
                <h3>{relationship.type}</h3>
                <p>{relationship.description}</p>
                <div className="actions">
                  <button 
                    onClick={() => onEdit(relationship.id)}
                    data-testid={`edit-${relationship.id}`}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => onDelete(relationship.id)}
                    data-testid={`delete-${relationship.id}`}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
