import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom'; // Import Link and useNavigate
import api from '../api'; // Ensure path is correct

function AddRelationshipPage() {
  const initialRelationshipState = {
    person1: '',
    person2: '',
    relationshipType: 'spouse', // Default relationship type
    attributes: {}, // Include attributes if your API supports them
  };
  const [relationship, setRelationship] = useState(initialRelationshipState);
  const [people, setPeople] = useState([]);
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate(); // Hook for navigation

  // Define valid relationship types (should match backend's VALID_RELATIONSHIP_TYPES)
  const relationshipTypes = [
      'spouse', 'parent', 'child', 'sibling', 'partner', 'friend',
      'grandparent', 'grandchild', 'aunt', 'uncle', 'nephew', 'niece', 'cousin',
      'step-parent', 'step-child', 'step-sibling', 'adopted child',
      'adoptive parent', 'godparent', 'godchild'
      // Add any other types defined in backend/src/relationship.py
  ];

  // Fetch people list on component mount
  useEffect(() => {
    const fetchPeople = async () => {
      setLoading(true); // Start loading before fetch
      setError(null); // Clear previous errors
      try {
        const peopleData = await api.getAllPeople();
        // Ensure peopleData is an array before setting state
        setPeople(Array.isArray(peopleData) ? peopleData : []);
      } catch (err) {
        console.error("Failed to load people:", err);
        setError('Failed to load people list. Please try again later.');
        setPeople([]); // Set to empty array on error
      } finally {
        setLoading(false); // Stop loading after fetch attempt
      }
    };

    fetchPeople();
  }, []); // Empty dependency array ensures this runs only once on mount

  // Handle changes in select dropdowns
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship({ ...relationship, [name]: value });
    setError(null); // Clear error when user changes input
  };

  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    // Basic validation
    if (!relationship.person1 || !relationship.person2) {
        setError("Please select both Person 1 and Person 2.");
        setLoading(false);
        return;
    }
    if (relationship.person1 === relationship.person2) {
        setError("Cannot create a relationship between the same person.");
        setLoading(false);
        return;
    }
    if (!relationship.relationshipType) {
        setError("Please select a relationship type.");
        setLoading(false);
        return;
    }

    // Prepare data matching the API expected format
    const dataToSend = {
        person1: relationship.person1,
        person2: relationship.person2,
        relationshipType: relationship.relationshipType,
        attributes: relationship.attributes || {} // Include attributes if needed
    };

    try {
      await api.createRelationship(dataToSend);
      setSuccessMessage('Relationship added successfully!');
      setRelationship(initialRelationshipState); // Reset form
      // Optionally navigate away or show message longer
      setTimeout(() => {
        setSuccessMessage(null);
        // navigate('/dashboard'); // Example: Redirect after success
      }, 3000);
    } catch (err) {
      // Extract more specific error message if available
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to add relationship.';
      setError(errorMsg);
      console.error("Add relationship error:", err.response || err);
    } finally {
      setLoading(false);
    }
  };

  return (
    // Use form-container class for consistent styling
    <div className="form-container">
      <h1>Add Relationship</h1>
      {/* Use message classes for feedback */}
      {successMessage && <div className="message success-message">{successMessage}</div>}
      {error && <div className="message error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Person 1 Dropdown */}
        <div className="form-group">
          <label htmlFor="person1">Person 1:</label>
          <select
            id="person1"
            name="person1" // Matches state key
            value={relationship.person1}
            onChange={handleInputChange}
            required // Basic HTML5 validation
            disabled={loading} // Disable while loading people or submitting
          >
            <option value="" disabled>-- Select Person 1 --</option>
            {/* *** FIX: Use person.person_id, person.first_name, person.last_name *** */}
            {people.map((person) => (
              <option key={person.person_id} value={person.person_id}>
                {person.first_name} {person.last_name} ({person.person_id.substring(0, 8)}...)
              </option>
            ))}
          </select>
        </div>

        {/* Person 2 Dropdown */}
        <div className="form-group">
          <label htmlFor="person2">Person 2:</label>
          <select
            id="person2"
            name="person2" // Matches state key
            value={relationship.person2}
            onChange={handleInputChange}
            required
            disabled={loading}
          >
            <option value="" disabled>-- Select Person 2 --</option>
            {/* *** FIX: Use person.person_id, person.first_name, person.last_name *** */}
            {people.map((person) => (
              <option key={person.person_id} value={person.person_id}>
                {person.first_name} {person.last_name} ({person.person_id.substring(0, 8)}...)
              </option>
            ))}
          </select>
        </div>

        {/* Relationship Type Dropdown */}
        <div className="form-group">
          <label htmlFor="relationshipType">Relationship Type:</label>
          <select
            id="relationshipType"
            name="relationshipType" // Matches state key
            value={relationship.relationshipType}
            onChange={handleInputChange}
            required
            disabled={loading}
          >
            {/* Default option is handled by initial state */}
            {relationshipTypes.map((type) => (
              <option key={type} value={type}>
                {/* Capitalize for display */}
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Add fields for attributes if needed here */}
        {/* Example:
        <div className="form-group">
          <label htmlFor="start_date">Start Date (Optional):</label>
          <input
            type="date"
            id="start_date"
            name="start_date" // This would need custom handling for attributes state
            value={relationship.attributes?.start_date || ''}
            onChange={handleAttributeChange} // Need to implement handleAttributeChange
            disabled={loading}
          />
        </div>
        */}

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem' }}>
            <button type="submit" disabled={loading}>
              {loading ? 'Adding...' : 'Add Relationship'}
            </button>
            <Link to="/dashboard" className="button" style={{ backgroundColor: 'var(--color-secondary)', textDecoration: 'none', textAlign: 'center' }}>
                Cancel
            </Link>
        </div>
      </form>
    </div>
  );
}

export default AddRelationshipPage;
