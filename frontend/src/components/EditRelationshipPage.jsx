import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom'; // Added useNavigate
import api from '../api'; // Ensure this path is correct

function EditRelationshipPage() {
  // State for relationship data, people list, loading, success, and error
  const [relationship, setRelationship] = useState({ person1_id: '', person2_id: '', rel_type: '', attributes: {} });
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false); // Separate saving state
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const { id } = useParams(); // Get relationship ID from URL
  const navigate = useNavigate(); // Hook for navigation

  // Define valid relationship types for the dropdown
  const relationshipTypes = ['spouse', 'parent', 'child', 'sibling', 'partner', 'friend', 'grandparent', 'grandchild', 'aunt', 'uncle', 'nephew', 'niece', 'cousin', 'step-parent', 'step-child', 'step-sibling', 'adopted child', 'adoptive parent', 'godparent', 'godchild']; // Add more as needed from backend

  // Fetch relationship details and list of people on mount or ID change
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      try {
        if (!id) {
            setError('No relationship ID provided in URL.');
            setLoading(false);
            return;
        }
        // Fetch relationship and people data concurrently
        const [relationshipData, peopleData] = await Promise.all([
          api.getRelationship(id),
          api.getAllPeople()
        ]);

        // Ensure fetched data has the expected structure
        setRelationship({
             person1_id: relationshipData.person1_id || '',
             person2_id: relationshipData.person2_id || '',
             rel_type: relationshipData.rel_type || '',
             attributes: relationshipData.attributes || {}
        });
        setPeople(peopleData || []); // Ensure people is an array

      } catch (err) {
        // Handle fetch errors
        const errorMsg = err.response?.data?.message || err.message || 'Failed to load relationship details or people list.';
        setError(errorMsg);
        console.error('Error loading relationship details:', err);
      } finally {
        setLoading(false); // Loading finished
      }
    };

    fetchData();
  }, [id]); // Re-run effect if ID changes

  // Handle changes in form inputs (select dropdowns)
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship(prevRel => ({ ...prevRel, [name]: value }));
  };

   // Handle changes in attribute inputs (example for a 'start_date' attribute)
   const handleAttributeChange = (event) => {
       const { name, value } = event.target;
       setRelationship(prevRel => ({
           ...prevRel,
           attributes: {
               ...prevRel.attributes,
               [name]: value // Update specific attribute
           }
       }));
   };


  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default submission
    setError(null);
    setSuccessMessage(null);
    setSaving(true); // Indicate saving state

    // Basic validation: Ensure different people are selected
    if (relationship.person1_id === relationship.person2_id) {
        setError("Cannot create a relationship between the same person.");
        setSaving(false);
        return;
    }

    // Prepare data for API (ensure attributes is included)
    const dataToSend = {
         person1: relationship.person1_id, // Match API expected key if different
         person2: relationship.person2_id, // Match API expected key if different
         relationshipType: relationship.rel_type, // Match API expected key if different
         attributes: relationship.attributes || {}
    };


    try {
      // Send updated data to the API
      await api.updateRelationship(id, dataToSend);
      setSuccessMessage('Relationship updated successfully!');
      setError(null);
      // Optionally navigate back or refresh data after a delay
      setTimeout(() => {
        setSuccessMessage(null);
        // navigate('/dashboard'); // Example navigation
      }, 3000);
    } catch (error) {
      // Handle submission errors
      const errorMsg = error.response?.data?.message || error.response?.data?.details || error.message || 'Failed to update relationship.';
       if (typeof errorMsg === 'object') {
           setError(Object.values(errorMsg).join('. '));
       } else {
           setError(errorMsg);
       }
      console.error('Error updating relationship:', error.response || error);
    } finally {
      setSaving(false); // Saving finished
    }
  };

  // Display loading indicator
  if (loading) {
    return <div>Loading relationship details...</div>;
  }

  // Display error if fetch failed
  if (error && !saving) { // Only show fetch error if not currently saving
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }

  // Render the form
  return (
    <div className="edit-relationship-page">
      <h1>Edit Relationship</h1>
      {/* Display general error messages */}
      {error && !saving && <div style={{ color: 'red', marginBottom: '10px' }}>Error: {error}</div>}
      {/* Display success message */}
      {successMessage && <div style={{ color: 'green', marginBottom: '10px' }}>{successMessage}</div>}

      <form onSubmit={handleSubmit}>
        {/* Dropdown for Person 1 */}
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="person1_id">Person 1:</label>
          <select id="person1_id" name="person1_id" value={relationship.person1_id} onChange={handleInputChange} required>
            <option value="" disabled>Select Person 1</option>
            {people.map((person) => (
              <option key={person.person_id} value={person.person_id}>
                {person.first_name} {person.last_name}
              </option>
            ))}
          </select>
        </div>

        {/* Dropdown for Person 2 */}
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="person2_id">Person 2:</label>
          <select id="person2_id" name="person2_id" value={relationship.person2_id} onChange={handleInputChange} required>
            <option value="" disabled>Select Person 2</option>
            {people.map((person) => (
              <option key={person.person_id} value={person.person_id}>
                {person.first_name} {person.last_name}
              </option>
            ))}
          </select>
        </div>

        {/* Dropdown for Relationship Type */}
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="rel_type">Relationship Type:</label>
          <select id="rel_type" name="rel_type" value={relationship.rel_type} onChange={handleInputChange} required>
             <option value="" disabled>Select Type</option>
            {relationshipTypes.map((type) => (
              <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option> // Capitalize for display
            ))}
          </select>
        </div>

         {/* Example for editing an attribute (e.g., start_date) */}
         <div style={{ marginBottom: '10px' }}>
             <label htmlFor="start_date">Start Date (Optional):</label>
             <input
                 type="date"
                 id="start_date"
                 name="start_date" // Must match the key in the attributes object
                 value={relationship.attributes?.start_date || ''} // Access nested attribute safely
                 onChange={handleAttributeChange}
             />
         </div>

        {/* Submit button with disabled state during saving */}
        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  );
}

export default EditRelationshipPage;
