import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom'; // Added Link
import api from '../api'; // Ensure this path is correct
import { useAuth } from '../context/AuthContext'; // Import useAuth

function EditRelationshipPage() {
  const { activeTreeId } = useAuth(); // Get activeTreeId from context
  const { id } = useParams(); // Get relationship ID from URL
  const navigate = useNavigate(); // Hook for navigation

  // State for relationship data, people list, loading, success, and error
  const [relationship, setRelationship] = useState({ person1_id: '', person2_id: '', relationship_type: '', attributes: {} });
  const [people, setPeople] = useState([]); // State for people list
  const [initialLoading, setInitialLoading] = useState(true); // For initial fetch
  const [loadingPeople, setLoadingPeople] = useState(false); // Separate loading for people list
  const [saving, setSaving] = useState(false); // Separate saving state
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [validationErrors, setValidationErrors] = useState({}); // For field-specific errors
  const fetchedTreeId = useRef(null); // Ref to store the tree ID for which people were fetched

  // Define valid relationship types (should match backend's RelationshipTypeEnum)
  const relationshipTypes = [
      'biological_parent', 'adoptive_parent', 'step_parent', 'foster_parent',
      'guardian', 'spouse_current', 'spouse_former', 'partner',
      'biological_child', 'adoptive_child', 'step_child', 'foster_child',
      'sibling_full', 'sibling_half', 'sibling_step', 'sibling_adoptive',
      'other'
  ];

  // Fetch relationship details and list of people on mount or ID change
  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      // Only fetch if activeTreeId is set and we have an ID
      if (!id || !activeTreeId) {
          if (isMounted) {
              setError('No relationship ID or active tree provided.');
              setInitialLoading(false);
              setPeople([]); // Clear people list
              fetchedTreeId.current = null;
          }
          return;
      }

      setInitialLoading(true);
      setError(null);
      setSuccessMessage(null);
      setValidationErrors({});

      // Fetch people list ONLY if needed (empty or tree ID changed)
      const shouldFetchPeople = people.length === 0 || fetchedTreeId.current !== activeTreeId;
      if (shouldFetchPeople) {
          setLoadingPeople(true);
      }

      try {
        // Fetch relationship details
        const relationshipPromise = api.getRelationship(id, activeTreeId); // Pass activeTreeId implicitly

        // Fetch people data only if necessary
        const peoplePromise = shouldFetchPeople ? api.getAllPeople(activeTreeId) : Promise.resolve(people); // Reuse existing if not needed

        // Fetch concurrently
        const [relationshipData, peopleData] = await Promise.all([
          relationshipPromise,
          peoplePromise
        ]);

        if (isMounted) {
            // Ensure fetched relationship data has the expected structure
            setRelationship({
                 person1_id: relationshipData.person1_id || '',
                 person2_id: relationshipData.person2_id || '',
                 relationship_type: relationshipData.relationship_type || '', // Use relationship_type from backend
                 attributes: relationshipData.custom_attributes || {} // Use custom_attributes from backend
            });

            // Update people list only if it was fetched
            if (shouldFetchPeople) {
                 setPeople(Array.isArray(peopleData) ? peopleData : []); // Ensure people is an array
                 fetchedTreeId.current = activeTreeId; // Store the ID for which we fetched
            }
        }

      } catch (err) {
        // Handle fetch errors
        if (isMounted) {
            const errorMsg = err.response?.data?.message || err.message || 'Failed to load relationship details or people list.';
            setError(errorMsg);
            setPeople([]); // Clear people on error
            fetchedTreeId.current = null;
            console.error('Error loading relationship details:', err.response || err);
        }
      } finally {
        if (isMounted) {
            setInitialLoading(false); // Initial loading finished
            if (shouldFetchPeople) {
                 setLoadingPeople(false); // People loading finished
            }
        }
      }
    };

    fetchData();
    return () => { isMounted = false; };
  // Dependencies: id, activeTreeId, and people.length (to trigger people refetch if cleared)
  }, [id, activeTreeId, people.length]);

  // Handle changes in form inputs (select dropdowns)
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setRelationship(prevRel => ({ ...prevRel, [name]: value }));
    // Clear validation errors when input changes
    if (validationErrors[name]) {
        setValidationErrors(prev => ({ ...prev, [name]: null }));
    }
    if ((name === 'person1_id' || name === 'person2_id') && validationErrors.person_ids) {
        setValidationErrors(prev => ({ ...prev, person_ids: null }));
    }
    if (name === 'relationship_type' && validationErrors.relationship_type) {
        setValidationErrors(prev => ({ ...prev, relationship_type: null }));
    }
  };

   // Handle changes in attribute inputs
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
    event.preventDefault(); // Prevent default submission
    setError(null);
    setSuccessMessage(null);
    setSaving(true); // Indicate saving state
    setValidationErrors({}); // Clear previous errors

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
        setSaving(false);
        return;
    }

    // Prepare data for API (ensure attributes is included)
    // Match backend expected keys: person1, person2, relationshipType
    const dataToSend = {
         person1: relationship.person1_id,
         person2: relationship.person2_id,
         relationshipType: relationship.relationship_type,
         attributes: relationship.attributes || {}
    };

    try {
      // Send updated data to the API, pass activeTreeId implicitly
      await api.updateRelationship(id, dataToSend, activeTreeId);
      setSuccessMessage('Relationship updated successfully!');
      setError(null);
      // Optionally navigate back or refresh data after a delay
      setTimeout(() => {
        setSuccessMessage(null);
        // navigate('/dashboard'); // Example navigation
      }, 3000);
    } catch (err) {
      // Handle submission errors
      const errorData = err.response?.data;
      let errorMsg = "Failed to update relationship.";
       if (errorData) {
           if (errorData.details && typeof errorData.details === 'object') {
                setValidationErrors(errorData.details);
                errorMsg = "Please correct the errors below.";
           } else {
               errorMsg = errorData.message || errorData.error || errorMsg;
           }
       } else {
           errorMsg = err.message || errorMsg;
       }
       setError(errorMsg);
      console.error('Error updating relationship:', err.response || err);
    } finally {
      setSaving(false); // Saving finished
    }
  };

  // Show message if no active tree is selected
  if (!activeTreeId && !initialLoading) {
      return (
          <div className="form-container">
              <h1>Edit Relationship</h1>
              <div className="message error-message">
                  No active family tree selected. Please select or create a tree on the <Link to="/dashboard">Dashboard</Link>.
              </div>
          </div>
      );
  }

  // Display loading indicator during initial fetch
  if (initialLoading) {
    return <div className="form-container">Loading relationship details...</div>;
  }

  // Display error if fetch failed significantly
  if (error && !relationship.person1_id && !initialLoading) {
       return <div className="form-container message error-message">Error loading details: {error}</div>;
  }

  // Render the form
  return (
    <div className="form-container">
      <h1>Edit Relationship</h1>
      {/* Display general error messages */}
      {error && !Object.keys(validationErrors).length > 0 && <div className="message error-message">{error}</div>}
      {/* Display success message */}
      {successMessage && <div className="message success-message">{successMessage}</div>}

      <form onSubmit={handleSubmit}>
        {/* Dropdown for Person 1 */}
        <div className="form-group">
          <label htmlFor="person1_id">Person 1:</label>
          <select
              id="person1_id"
              name="person1_id"
              value={relationship.person1_id}
              onChange={handleInputChange}
              required
              disabled={saving || loadingPeople}
              aria-invalid={!!validationErrors.person_ids}
              aria-describedby={validationErrors.person_ids ? "person-ids-error" : undefined}
          >
            <option value="" disabled>-- Select Person 1 --</option>
            {loadingPeople ? (
                 <option value="" disabled>Loading people...</option>
            ) : (
                 people.map((person) => (
                   // Use person.id which corresponds to the UUID
                   <option key={person.id} value={person.id}>
                     {person.first_name} {person.last_name} ({person.id.substring(0, 8)}...)
                   </option>
                 ))
            )}
          </select>
           {validationErrors.person_ids && <div id="person-ids-error" className="field-error">{validationErrors.person_ids}</div>}
        </div>

        {/* Dropdown for Person 2 */}
        <div className="form-group">
          <label htmlFor="person2_id">Person 2:</label>
          <select
              id="person2_id"
              name="person2_id"
              value={relationship.person2_id}
              onChange={handleInputChange}
              required
              disabled={saving || loadingPeople}
              aria-invalid={!!validationErrors.person_ids}
              aria-describedby={validationErrors.person_ids ? "person-ids-error" : undefined}
          >
            <option value="" disabled>-- Select Person 2 --</option>
            {loadingPeople ? (
                 <option value="" disabled>Loading people...</option>
            ) : (
                 people.map((person) => (
                   // Use person.id which corresponds to the UUID
                   <option key={person.id} value={person.id}>
                     {person.first_name} {person.last_name} ({person.id.substring(0, 8)}...)
                   </option>
                 ))
            )}
          </select>
           {/* Error message displayed under Person 1 dropdown */}
        </div>

        {/* Dropdown for Relationship Type */}
        <div className="form-group">
          <label htmlFor="relationship_type">Relationship Type:</label>
          <select
              id="relationship_type"
              name="relationship_type"
              value={relationship.relationship_type}
              onChange={handleInputChange}
              required
              disabled={saving}
              aria-invalid={!!validationErrors.relationship_type}
              aria-describedby={validationErrors.relationship_type ? "rel-type-error" : undefined}
          >
             <option value="" disabled>-- Select Type --</option>
            {relationshipTypes.map((type) => (
              <option key={type} value={type}>
                  {type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
              </option> // Capitalize for display
            ))}
          </select>
           {validationErrors.relationship_type && <div id="rel-type-error" className="field-error">{validationErrors.relationship_type}</div>}
        </div>

         {/* Custom Attributes Section */}
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
                         disabled={saving}
                         style={{ width: '150px' }}
                         aria-label={`Attribute ${index + 1} Name`}
                     />
                      <input
                         type="text"
                         placeholder="Attribute Value"
                         value={value}
                         onChange={(e) => handleAttributeChange({ target: { name: key, value: e.target.value } })}
                         disabled={saving}
                         style={{ flexGrow: 1 }}
                         aria-label={`Attribute ${index + 1} Value`}
                     />
                     <button
                        type="button"
                        onClick={() => removeCustomAttribute(key)}
                        disabled={saving}
                        style={{ width: 'auto', padding: '5px 10px', backgroundColor: 'var(--color-error-text)' }}
                        aria-label={`Remove attribute ${key}`}
                     >
                         Remove
                     </button>
                 </div>
             ))}
             <button type="button" onClick={addCustomAttribute} disabled={saving} style={{ width: 'auto', marginTop: '10px' }} className="secondary-button">
                 Add Attribute
             </button>
              {validationErrors.attributes && <div className="field-error">{validationErrors.attributes}</div>}
         </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
            <Link to="/dashboard" className="button secondary-button">Cancel</Link>
            <button type="submit" disabled={saving || loadingPeople}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
        </div>
      </form>
    </div>
  );
}

export default EditRelationshipPage;
