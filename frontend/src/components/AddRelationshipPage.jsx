import React, { useState, useEffect } from 'react';
import api from '../api';

function AddRelationshipPage() {
  const [relationship, setRelationship] = useState({
    person1: '',
    person2: '',
    relationshipType: 'spouse', // Default relationship type
  });
  const [people, setPeople] = useState([]);
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const relationshipTypes = ['spouse', 'parent', 'child', 'sibling'];

  useEffect(() => {
    const fetchPeople = async () => {
      try {
        const peopleData = await api.getAllPeople();
        setPeople(peopleData);
      } catch (err) {
        setError({ type: 'network', message: 'Failed to load people.' });
      }
    };

    fetchPeople();
  }, []);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship({ ...relationship, [name]: value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await api.createRelationship(relationship);
      setSuccessMessage('Relationship added successfully!');
      setRelationship({
        person1: '',
        person2: '',
        relationshipType: 'spouse',
      });
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err) {
      setError({
        type: "error",
        message: err.message || 'Failed to add relationship.',
      });
    } finally {
      setLoading(false);
    }
  };

  const getErrorMessage = () => {
    if (!error) return null;
  
    switch (error.type) {
      case 'network':
        return "Network error. Please check your connection.";
      case 'validation':
        return "Invalid input. Please check the fields.";
      default:
        return error.message || "An unexpected error occurred.";
    }
  };

  return (
    <div>
      <h1>Add Relationship</h1>
      {successMessage && <div className="success-message">{successMessage}</div>}
      {error && <div className="error-message">{getErrorMessage()}</div>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="person1">Person 1:</label>
          <select
            id="person1"
            name="person1"
            value={relationship.person1}
            onChange={handleInputChange}
          >
            <option value="">Select a person</option>
            {people.map((person) => (
              <option key={person.id} value={person.id}>
                {person.firstName} {person.lastName}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="person2">Person 2:</label>
          <select
            id="person2"
            name="person2"
            value={relationship.person2}
            onChange={handleInputChange}
          >
            <option value="">Select a person</option>
            {people.map((person) => (
              <option key={person.id} value={person.id}>
                {person.firstName} {person.lastName}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="relationshipType">Relationship Type:</label>
          <select
            id="relationshipType"
            name="relationshipType"
            value={relationship.relationshipType}
            onChange={handleInputChange}
          >
            {relationshipTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={loading}>
          Add Relationship
        </button>
      </form>
    </div>
  );
}

export default AddRelationshipPage;