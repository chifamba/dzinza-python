import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom'; // Import Link and useNavigate
import api from '../api'; // Ensure path is correct
import { useAuth } from '../context/AuthContext'; // Import useAuth

function AddRelationshipPage() {
  const { activeTreeId } = useAuth(); // Get activeTreeId from context
  const navigate = useNavigate(); // Hook for navigation

  const initialRelationshipState = {
    person1_id: '', // Changed to person1_id to match backend model
    person2_id: '', // Changed to person2_id to match backend model
    relationship_type: '', // Changed to relationship_type to match backend model, default to empty
    attributes: {}, // Include attributes if your API supports them
  };
  const [relationship, setRelationship] = useState(initialRelationshipState);
  const [people, setPeople] = useState([]); // State for people list
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({}); // For field-specific errors
  const [loading, setLoading] = useState(false); // For form submission
  const [loadingPeople, setLoadingPeople] = useState(false); // Separate loading state for people list
  const fetchedTreeId = useRef(null); // Ref to store the tree ID for which people were fetched

  // Define valid relationship types (should match backend's RelationshipTypeEnum)
  const relationshipTypes = [
      'biological_parent', 'adoptive_parent', 'step_parent', 'foster_parent',
      'guardian', 'spouse_current', 'spouse_former', 'partner',
      'biological_child', 'adoptive_child', 'step_child', 'foster_child',
      'sibling_full', 'sibling_half', 'sibling_step', 'sibling_adoptive',
      'other'
  ];

  // Fetch people list ONLY if activeTreeId changes or people list is empty
  useEffect(() => {
    let isMounted = true;
    const fetchPeople = async () => {
      // Only fetch if activeTreeId is set AND (people list is empty OR the activeTreeId has changed)
      if (!activeTreeId || (people.length > 0 && fetchedTreeId.current === activeTreeId)) {
          // No need to fetch if tree ID hasn't changed and we already have people
          // Or if no tree ID is selected
          if (!activeTreeId && isMounted) {
              // Clear people list if no tree is active
              setPeople([]);
              fetchedTreeId.current = null;
          }
          return;
      }

      setLoadingPeople(true); // Start loading before fetch
      setError(null); // Clear previous errors
      try {
        // Fetch people for the active tree (api.getAllPeople uses session active_tree_id)
        const peopleData = await api.getAllPeople(activeTreeId);
        // Ensure peopleData is an array before setting state
        if (isMounted) {
             setPeople(Array.isArray(peopleData) ? peopleData : []);
             fetchedTreeId.current = activeTreeId; // Store the ID for which we fetched
        }
      } catch (err) {
        console.error("Failed to load people:", err.response || err);
        if (isMounted) {
            const errorMsg = err.response?.data?.message || err.message || 'Failed to load people list.';
            setError(errorMsg);
            setPeople([]); // Set to empty array on error
            fetchedTreeId.current = null; // Reset fetched ID on error
        }
      } finally {
        if (isMounted) setLoadingPeople(false); // Stop loading after fetch attempt
      }
    };

    fetchPeople();
    return () => { isMounted = false; };
  // Dependencies: activeTreeId and the people array itself (to trigger refetch if cleared)
  }, [activeTreeId, people.length]); // Re-run if activeTreeId changes OR if people array becomes empty

  // Handle changes in select dropdowns and other inputs
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship({ ...relationship, [name]: value });
    // Clear validation error for this field when user changes input
     if (validationErrors[name]) {
         setValidationErrors(prevErrors => ({ ...prevErrors, [name]: null }));
     }
     // Clear general person ID error if both are now selected
     if (name === 'person1_id' || name === 'person2_id') {
         if (validationErrors.person_ids) {
              setValidationErrors(prevErrors => ({ ...prevErrors, person_ids: null }));
         }
     }
  };

   // Handle changes for custom attributes (similar to Person pages)
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

   // Add a new custom attribute field
   const addCustomAttribute = () => {
       const newKey = `attribute_${Object.keys(relationship.attributes).length + 1}`;
       setRelationship(prevRel => ({
           ...prevRel,
           attributes: {
               ...prevRel.attributes,
               [newKey]: ''
           }
       }));
   };

   // Remove a custom attribute field
   const removeCustomAttribute = (keyToRemove) => {
       setRelationship(prevRel => {
           const updatedAttributes = { ...prevRel.attributes };
           delete updatedAttributes[keyToRemove];
           return { ...prevRel, attributes: updatedAttributes };
       });
   };


  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!activeTreeId) {
        setError("No active family tree selected. Cannot add relationship.");
        return;
    }

    setLoading(true); // Indicate submission loading
    setError(null);
    setSuccessMessage(null);
    setValidationErrors({});

    // Basic client-side validation
    let currentValidationErrors = {};
    if (!relationship.person1_id || !relationship.person2_id) {
        currentValidationErrors.person_ids = "Please select both Person 1 and Person 2.";
    } else if (relationship.person1_id === relationship.person2_id) {
        currentValidationErrors.person_ids = "Cannot create a relationship between the same person.";
    }
    if (!relationship.relationship_type) {
        currentValidationErrors.relationship_type = "Please select a relationship type.";
    }

    if (Object.keys(currentValidationErrors).length > 0) {
        setValidationErrors(currentValidationErrors);
        setLoading(false);
        return;
    }

    // Prepare data matching the API expected format (using person1, person2, relationshipType keys)
    const dataToSend = {
        person1: relationship.person1_id, // Match API key
        person2: relationship.person2_id, // Match API key
        relationshipType: relationship.relationship_type, // Match API key
        attributes: relationship.attributes || {} // Include attributes
        // Add start_date, end_date, certainty_level, notes if you add inputs for them
    };

    try {
      // Pass activeTreeId implicitly via session managed by api.js
      await api.createRelationship(dataToSend, activeTreeId);
      setSuccessMessage('Relationship added successfully!');
      setRelationship(initialRelationshipState); // Reset form
      // Optionally navigate away or show message longer
      setTimeout(() => {
        setSuccessMessage(null);
        navigate('/dashboard'); // Redirect after success
      }, 2000); // Navigate after 2 seconds
    } catch (err) {
      // Extract more specific error message if available
       const errorData = err.response?.data;
       let errorMsg = "Failed to add relationship.";
       if (errorData) {
           if (errorData.details && typeof errorData.details === 'object') {
                // Backend returns field-specific errors in 'details'
                setValidationErrors(errorData.details);
                errorMsg = "Please correct the errors below."; // General message for validation issues
           } else {
               // Handle other backend error messages
               errorMsg = errorData.message || errorData.error || errorMsg;
           }
       } else {
           // Handle network or other errors
           errorMsg = err.message || errorMsg;
       }
       setError(errorMsg);
      console.error("Add relationship error:", err.response || err);
    } finally {
      setLoading(false); // Stop loading after attempt
    }
  };

   // Show a message if no active tree is selected
  if (!activeTreeId && !loadingPeople) { // Only show this after people loading check
      return (
          <div className="form-container">
              <h1>Add Relationship</h1>
              <div className="message error-message">
                  Please select or create a family tree on the <Link to="/dashboard">Dashboard</Link> before adding relationships.
              </div>
          </div>
      );
  }


  return (
    // Use form-container class for consistent styling
    <div className="form-container">
      <h1>Add Relationship</h1>
      {/* Use message classes for feedback */}
      {successMessage && <div className="message success-message">{successMessage}</div>}
      {error && !validationErrors.person_ids && !validationErrors.relationship_type && <div className="message error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Person 1 Dropdown */}
        <div className="form-group">
          <label htmlFor="person1_id">Person 1:</label>
          <select
            id="person1_id"
            name="person1_id" // Matches state key
            value={relationship.person1_id}
            onChange={handleInputChange}
            required // Basic HTML5 validation
            disabled={loading || loadingPeople} // Disable while loading people or submitting
            aria-invalid={!!validationErrors.person_ids} // Indicate invalid field for accessibility
            aria-describedby={validationErrors.person_ids ? "person-ids-error" : undefined}
          >
            <option value="" disabled>-- Select Person 1 --</option>
            {loadingPeople ? (
                <option value="" disabled>Loading people...</option>
            ) : (
                 people.map((person) => (
                   // Use person.id which corresponds to the UUID from the backend Person model
                   <option key={person.id} value={person.id}>
                     {person.first_name} {person.last_name} ({person.id.substring(0, 8)}...)
                   </option>
                 ))
            )}
          </select>
           {validationErrors.person_ids && <div id="person-ids-error" className="field-error">{validationErrors.person_ids}</div>}
        </div>

        {/* Person 2 Dropdown */}
        <div className="form-group">
          <label htmlFor="person2_id">Person 2:</label>
          <select
            id="person2_id"
            name="person2_id" // Matches state key
            value={relationship.person2_id}
            onChange={handleInputChange}
            required
            disabled={loading || loadingPeople}
            aria-invalid={!!validationErrors.person_ids} // Indicate invalid field for accessibility
            aria-describedby={validationErrors.person_ids ? "person-ids-error" : undefined}
          >
            <option value="" disabled>-- Select Person 2 --</option>
             {loadingPeople ? (
                <option value="" disabled>Loading people...</option>
            ) : (
                 people.map((person) => (
                   // Use person.id which corresponds to the UUID from the backend Person model
                   <option key={person.id} value={person.id}>
                     {person.first_name} {person.last_name} ({person.id.substring(0, 8)}...)
                   </option>
                 ))
            )}
          </select>
           {/* Error message is displayed under Person 1 dropdown */}
        </div>

        {/* Relationship Type Dropdown */}
        <div className="form-group">
          <label htmlFor="relationship_type">Relationship Type:</label>
          <select
            id="relationship_type"
            name="relationship_type" // Matches state key
            value={relationship.relationship_type}
            onChange={handleInputChange}
            required
            disabled={loading}
            aria-invalid={!!validationErrors.relationship_type} // Indicate invalid field for accessibility
            aria-describedby={validationErrors.relationship_type ? "rel-type-error" : undefined}
          >
            <option value="" disabled>-- Select Type --</option> {/* Added empty option */}
            {relationshipTypes.map((type) => (
              <option key={type} value={type}>
                {/* Capitalize for display */}
                {type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
              </option>
            ))}
          </select>
           {validationErrors.relationship_type && <div id="rel-type-error" className="field-error">{validationErrors.relationship_type}</div>}
        </div>

         {/* Custom Attributes Section - Similar to Person pages */}
         <div className="form-group">
             <label>Custom Attributes:</label>
             {Object.entries(relationship.attributes).map(([key, value], index) => (
                 <div key={`attr-${index}`} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '5px' }}>
                     <input
                         type="text"
                         placeholder="Attribute Name"
                         value={key}
                         onChange={(e) => {
                             const newAttributes = { ...relationship.attributes };
                             const oldValue = newAttributes[key];
                             delete newAttributes[key];
                             newAttributes[e.target.value] = oldValue;
                             setRelationship({ ...relationship, attributes: newAttributes });
                         }}
                         disabled={loading}
                         style={{ width: '150px' }} // Adjust width for key input
                         aria-label={`Attribute ${index + 1} Name`}
                     />
                      <input
                         type="text"
                         placeholder="Attribute Value"
                         value={value}
                         onChange={(e) => handleAttributeChange({ target: { name: key, value: e.target.value } })}
                         disabled={loading}
                         style={{ flexGrow: 1 }} // Allow value input to take remaining space
                         aria-label={`Attribute ${index + 1} Value`}
                     />
                     <button
                        type="button"
                        onClick={() => removeCustomAttribute(key)}
                        disabled={loading}
                        style={{ width: 'auto', padding: '5px 10px', backgroundColor: 'var(--color-error-text)' }}
                        aria-label={`Remove attribute ${key}`}
                     >
                         Remove
                     </button>
                 </div>
             ))}
             <button type="button" onClick={addCustomAttribute} disabled={loading} style={{ width: 'auto', marginTop: '10px' }} className="secondary-button">
                 Add Attribute
             </button>
              {validationErrors.attributes && <div className="field-error">{validationErrors.attributes}</div>}
         </div>


        {/* Buttons */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}> {/* Align buttons to the right, allow wrapping */}
            <Link to="/dashboard" className="button secondary-button"> {/* Use secondary-button class */}
                Cancel
            </Link>
            <button type="submit" disabled={loading || loadingPeople}>
              {loading ? 'Adding...' : 'Add Relationship'}
            </button>
        </div>
      </form>
    </div>
  );
}

export default AddRelationshipPage;
