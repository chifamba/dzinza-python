import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom'; // Added Link
import api from '../api'; // Ensure this path is correct
import { useAuth } from '../context/AuthContext'; // Import useAuth

function EditPersonPage() {
  const { activeTreeId } = useAuth(); // Get activeTreeId from context
  const navigate = useNavigate(); // Hook for navigation
  const { id } = useParams(); // Get person ID from URL parameter

  // State for person data, loading, success, and error messages
  const [person, setPerson] = useState({
    first_name: '',
    last_name: '',
    nickname: '',
    birth_date: '',
    death_date: '',
    place_of_birth: '',
    place_of_death: '',
    gender: '', // Default to empty
    notes: '',
    custom_attributes: {} // Initialize custom attributes as an empty object
  });
  const [initialLoading, setInitialLoading] = useState(true); // For initial fetch
  const [saving, setSaving] = useState(false); // Separate state for saving operation
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({}); // For field-specific errors

   // Define valid genders (should match backend's Person.gender constraint)
  const validGenders = ['Male', 'Female', 'Other', 'Unknown'];


  // Fetch person data when the component mounts or ID/activeTreeId changes
  useEffect(() => {
    let isMounted = true; // Flag to prevent state update on unmounted component
    const fetchPerson = async () => {
      // Only fetch if activeTreeId is set and we have an ID
      if (!id || !activeTreeId) {
          if (isMounted) {
              setError('No person ID or active tree provided.');
              setInitialLoading(false);
          }
          return;
      }

      setInitialLoading(true);
      setError(null);
      setSuccess(false);
      setValidationErrors({});
      try {
        // Fetch person data from API, pass activeTreeId implicitly via session
        const data = await api.getPerson(id, activeTreeId);
        if (isMounted) {
            // Format dates for input type="date" (YYYY-MM-DD) and handle nulls
            const formattedData = {
              ...data,
              first_name: data.first_name || '',
              last_name: data.last_name || '',
              nickname: data.nickname || '',
              birth_date: data.birth_date ? data.birth_date.split('T')[0] : '',
              death_date: data.death_date ? data.death_date.split('T')[0] : '',
              place_of_birth: data.place_of_birth || '',
              place_of_death: data.place_of_death || '',
              gender: data.gender || '', // Set to empty string if null
              notes: data.notes || '',
              custom_attributes: data.custom_attributes || {} // Ensure it's an object
            };
            setPerson(formattedData);
        }
      } catch (err) {
        // Handle fetch errors
        const errorMsg = err.response?.data?.message || err.message || "Failed to fetch person details";
        if (isMounted) setError(errorMsg);
        console.error('Error fetching person:', err.response || err);
      } finally {
        if (isMounted) setInitialLoading(false); // Loading finished
      }
    };

    fetchPerson();

    // Cleanup function to set isMounted to false when component unmounts
    return () => {
        isMounted = false;
    };
  }, [id, activeTreeId]); // Re-run effect if the ID or activeTreeId changes

  // Handle changes in form inputs
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson(prevPerson => ({ ...prevPerson, [name]: value }));
     // Clear validation error for this field when user types
     if (validationErrors[name]) {
         setValidationErrors(prevErrors => ({ ...prevErrors, [name]: null }));
     }
  };

   // Handle changes for custom attributes
   const handleAttributeChange = (event) => {
       const { name, value } = event.target;
       setPerson(prevPerson => ({
           ...prevPerson,
           custom_attributes: {
               ...prevPerson.custom_attributes,
               [name]: value // Update specific attribute
           }
       }));
   };

   // Add a new custom attribute field
   const addCustomAttribute = () => {
       // Add a placeholder attribute, user will rename/fill
       const newKey = `attribute_${Object.keys(person.custom_attributes).length + 1}`;
       setPerson(prevPerson => ({
           ...prevPerson,
           custom_attributes: {
               ...prevPerson.custom_attributes,
               [newKey]: ''
           }
       }));
   };

   // Remove a custom attribute field
   const removeCustomAttribute = (keyToRemove) => {
       setPerson(prevPerson => {
           const updatedAttributes = { ...prevPerson.custom_attributes };
           delete updatedAttributes[keyToRemove];
           return { ...prevPerson, custom_attributes: updatedAttributes };
       });
   };


  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default form submission

     if (!activeTreeId) {
        setError("No active family tree selected. Cannot save changes.");
        return;
    }

    setSaving(true); // Indicate saving state
    setError(null);
    setSuccess(false);
    setValidationErrors({}); // Clear previous validation errors

    // Prepare data for API (ensure dates are null if empty, otherwise keep YYYY-MM-DD)
    const dataToSend = {
      ...person,
      birth_date: person.birth_date || null,
      death_date: person.death_date || null,
      custom_attributes: person.custom_attributes || {} // Ensure it's an object
    };

    try {
      // Send updated data to the API, pass activeTreeId implicitly via session
      await api.updatePerson(id, dataToSend, activeTreeId);
      setSuccess(true); // Show success message
      setError(null);
      // Optionally navigate back after a delay
      setTimeout(() => {
        setSuccess(false);
        // navigate('/dashboard'); // Example: navigate back to dashboard
      }, 2000); // Hide success message after 2 seconds
    } catch (err) {
      // Handle submission errors
      const errorData = err.response?.data;
      let errorMsg = "Failed to update person details.";

      if (errorData) {
           if (errorData.details && typeof errorData.details === 'object') {
                // Handle structured validation errors from backend
                setValidationErrors(errorData.details);
                errorMsg = "Please correct the errors below."; // General message
           } else {
                // Handle general error message from backend
                errorMsg = errorData.message || errorData.error || errorMsg;
           }
      } else {
           // Handle network or other errors
           errorMsg = err.message || errorMsg;
      }

      setError(errorMsg); // Set general error message
      console.error('Error updating person:', err.response || err);
    } finally {
      setSaving(false); // Saving finished
    }
  };

  // Show a message if no active tree is selected
  if (!activeTreeId && !initialLoading) { // Only show this after initial loading check
      return (
          <div className="form-container">
              <h1>Edit Person</h1>
              <div className="message error-message">
                  No active family tree selected. Please select or create a tree on the <Link to="/dashboard">Dashboard</Link>.
              </div>
          </div>
      );
  }


  // Display loading indicator during initial fetch
  if (initialLoading) {
    return <div className="form-container">Loading person details...</div>;
  }

  // Display error if initial fetch failed significantly and no person data was loaded
  if (error && !person.first_name && !initialLoading) {
       return <div className="form-container message error-message">Error loading details: {error}</div>;
  }

  // Render the form
  return (
    <div className="form-container">
      <h1>Edit Person: {person.first_name} {person.last_name}</h1>
      {/* Display general error messages */}
      {error && <div className="message error-message">{error}</div>}
      {/* Display success message */}
      {success && <div className="message success-message">Person updated successfully!</div>}

      <form onSubmit={handleSubmit}>
        {/* Form fields for person details */}
        <div className="form-group">
          <label htmlFor="first_name">First Name:</label>
          {/* Input uses global styles */}
          <input type="text" id="first_name" name="first_name" value={person.first_name} onChange={handleInputChange} required disabled={saving} />
           {validationErrors.first_name && <div className="field-error">{validationErrors.first_name}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="last_name">Last Name:</label>
          <input type="text" id="last_name" name="last_name" value={person.last_name} onChange={handleInputChange} disabled={saving} />
           {validationErrors.last_name && <div className="field-error">{validationErrors.last_name}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="nickname">Nickname:</label>
          <input type="text" id="nickname" name="nickname" value={person.nickname} onChange={handleInputChange} disabled={saving} />
        </div>
        <div className="form-group">
          <label htmlFor="birth_date">Date of Birth:</label>
          <input type="date" id="birth_date" name="birth_date" value={person.birth_date} onChange={handleInputChange} disabled={saving} />
           {validationErrors.birth_date && <div className="field-error">{validationErrors.birth_date}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="place_of_birth">Place of Birth:</label>
          <input type="text" id="place_of_birth" name="place_of_birth" value={person.place_of_birth} onChange={handleInputChange} disabled={saving} />
        </div>
        <div className="form-group">
          <label htmlFor="death_date">Date of Death:</label>
          <input type="date" id="death_date" name="death_date" value={person.death_date} onChange={handleInputChange} disabled={saving} />
           {validationErrors.death_date && <div className="field-error">{validationErrors.death_date}</div>}
           {validationErrors.date_comparison && <div className="field-error">{validationErrors.date_comparison}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="place_of_death">Place of Death:</label>
          <input type="text" id="place_of_death" name="place_of_death" value={person.place_of_death} onChange={handleInputChange} disabled={saving} />
        </div>
        <div className="form-group">
          <label htmlFor="gender">Gender:</label>
          <select id="gender" name="gender" value={person.gender} onChange={handleInputChange} disabled={saving}>
             <option value="">-- Select Gender --</option> {/* Added empty option */}
            {validGenders.map(genderOption => (
                <option key={genderOption} value={genderOption}>{genderOption}</option>
            ))}
          </select>
           {validationErrors.gender && <div className="field-error">{validationErrors.gender}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="notes">Notes:</label>
          <textarea id="notes" name="notes" value={person.notes} onChange={handleInputChange} rows="4" disabled={saving} />
        </div>

         {/* Custom Attributes Section - Similar to AddPersonPage */}
        <div className="form-group">
            <label>Custom Attributes:</label>
            {Object.entries(person.custom_attributes).map(([key, value]) => (
                <div key={key} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '5px' }}>
                    <input
                        type="text"
                        placeholder="Attribute Name"
                        value={key}
                        onChange={(e) => {
                            const newAttributes = { ...person.custom_attributes };
                            const oldValue = newAttributes[key];
                            delete newAttributes[key];
                            newAttributes[e.target.value] = oldValue;
                            setPerson({ ...person, custom_attributes: newAttributes });
                        }}
                        disabled={saving}
                        style={{ width: '150px' }} // Adjust width for key input
                    />
                     <input
                        type="text"
                        placeholder="Attribute Value"
                        value={value}
                        onChange={(e) => handleAttributeChange({ target: { name: key, value: e.target.value } })}
                        disabled={saving}
                        style={{ flexGrow: 1 }} // Allow value input to take remaining space
                    />
                    <button type="button" onClick={() => removeCustomAttribute(key)} disabled={saving} style={{ width: 'auto', padding: '5px 10px', backgroundColor: 'var(--color-error-text)' }}>
                        Remove
                    </button>
                </div>
            ))}
            <button type="button" onClick={addCustomAttribute} disabled={saving} style={{ width: 'auto', marginTop: '10px', backgroundColor: 'var(--color-secondary)' }}>
                Add Attribute
            </button>
             {validationErrors.custom_attributes && <div className="field-error">{validationErrors.custom_attributes}</div>}
        </div>


        {/* Submit button with disabled state during saving */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem', justifyContent: 'flex-end' }}> {/* Align buttons to the right */}
             <Link to="/dashboard" className="button secondary-button">Cancel</Link> {/* Use secondary-button class */}
            <button
                type="submit"
                disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
        </div>
      </form>
    </div>
  );
}

export default EditPersonPage;
