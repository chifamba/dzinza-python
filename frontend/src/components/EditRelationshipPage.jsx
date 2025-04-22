import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api';

function EditRelationshipPage() {
  const [relationship, setRelationship] = useState({ person1: '', person2: '', relationshipType: '' });
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState({ message: null, type: null });
  const [successMessage, setSuccessMessage] = useState(null);
  const { id } = useParams();

  const relationshipTypes = ['spouse', 'parent', 'child', 'sibling'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const relationshipData = await api.getRelationship(id);
        const peopleData = await api.getAllPeople();
        setRelationship(relationshipData);
        setPeople(peopleData);
      } catch (err) {
        setError({
          message: 'Failed to load relationship details.',
          type: 'fetch',
        });
        console.error('Error loading relationship details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship({ ...relationship, [name]: value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError({ message: null, type: null });
    try {
      await api.updateRelationship(id, relationship);
      setSuccessMessage('Relationship updated successfully!');
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      setError({ message: errorMessage, type: 'submit' });
      console.error('Error updating relationship:', error);
    }
  };

  const getErrorMessage = (error) => {
    if (error.response) {
      return error.response.data.message || 'An error occurred while processing your request.';
    } else if (error.request) {
      return 'Network error. Please check your connection and try again.';
    } else {
      return 'An unexpected error occurred.';
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error.message) {
    return (
      <div>
        <div>Error: {error.message}</div>
      </div>
    );
  }
  if (successMessage) {
      return <div className="success-message">{successMessage}</div>
    
  }
  

  if (successMessage) {
    return <div>{successMessage}</div>;
  }
  return (
    
    <div className="edit-relationship-page">
        <h1>Edit Relationship</h1>
        <form onSubmit={handleSubmit}>
            <div>
                <label htmlFor="person1">Person 1:</label>
                <select id="person1" name="person1" value={relationship.person1} onChange={handleInputChange}>
                    {people.map((person) => (
                        <option key={person.id} value={person.id}>
                            {person.firstName} {person.lastName}
                        </option>
                    ))}
                </select>
            </div>
            <div>
                <label htmlFor="person2">Person 2:</label>
                <select id="person2" name="person2" value={relationship.person2} onChange={handleInputChange}>
                    {people.map((person) => (
                        <option key={person.id} value={person.id}>
                            {person.firstName} {person.lastName}
                        </option>
                    ))}
                </select>
            </div>
            <div>
                <label htmlFor="relationshipType">Relationship Type:</label>
                <select id="relationshipType" name="relationshipType" value={relationship.relationshipType} onChange={handleInputChange}>
                    {relationshipTypes.map((type) => (
                        <option key={type} value={type} >{type}</option>
                    ))}
                </select>
            </div>
            <button type="submit" disabled={loading}>Save Changes</button>
        </form>
    </div>
  );
}

export default EditRelationshipPage;