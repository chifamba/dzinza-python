import React, { useState } from 'react';
import api from '../api'; // Ensure path is correct
import { Link, useNavigate } from 'react-router-dom'; // Import Link and useNavigate
import { useAuth } from '../context/AuthContext'; // Import useAuth

function AddPersonPage() {
  const { activeTreeId } = useAuth(); // Get activeTreeId from context
  const navigate = useNavigate(); // Hook for navigation

  const initialPersonState = {
      first_name: '', last_name: '', nickname: '',
      birth_date: '', death_date: '', // Use empty string for date inputs
      place_of_birth: '', place_of_death: '',
      gender: '', // Default to empty, let backend handle default or validation
      notes: '',
      custom_attributes: {} // Initialize custom attributes as an empty object
  };
  const [person, setPerson] = useState(initialPersonState);
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Define valid genders (should match backend's Person.gender constraint)
  const validGenders = ['Male', 'Female', 'Other', 'Unknown'];


  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson({ ...person, [name]: value });
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


  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!activeTreeId) {
        setError("No active family tree selected. Please select or create a tree on the dashboard.");
        return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    setValidationErrors({});

    const dataToSend = {
        ...person,
        birth_date: person.birth_date || null, // Send null if empty string
        death_date: person.death_date || null, // Send null if empty string
        // Ensure custom_attributes is an object, even if empty
        custom_attributes: person.custom_attributes || {},
        // Backend determines is_living based on death_date if not provided
        // is_living: person.is_living // Only send if you have a checkbox/input for it
    };

    try {
      // Create the person - backend will automatically create a PersonTreeAssociation
      const createdPerson = await api.createPerson(dataToSend, activeTreeId);
      setSuccessMessage('Person added successfully to the current family tree!');
      setPerson(initialPersonState); // Reset form
      // Optionally navigate back to dashboard after success
      setTimeout(() => {
          setSuccessMessage(null);
          navigate('/dashboard');
      }, 2000); // Navigate after 2 seconds
    } catch (err) {
       const errorData = err.response?.data;
       let errorMsg = "Failed to add person.";
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
       console.error("Add person error:", err.response || err);
    } finally {
      setLoading(false);
    }
  };

  // Show a message if no active tree is selected
  if (!activeTreeId) {
      return (
          <div className="form-container">
              <h1>Add New Person</h1>
              <div className="message error-message">
                  Please select or create a family tree on the <Link to="/dashboard">Dashboard</Link> before adding people.
              </div>
          </div>
      );
  }


  return (
    // Use form-container class
    <div className="form-container">
      <h1>Add New Person</h1>
      {/* Use message classes */}
      {successMessage && <div className="message success-message">{successMessage}</div>}
      {error && <div className="message error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        {/* Use form-group class */}
        <div className="form-group">
          <label htmlFor="first_name">First Name:</label>
          {/* Input uses global styles */}
          <input type="text" id="first_name" name="first_name" value={person.first_name} onChange={handleInputChange} required disabled={loading} />
           {validationErrors.first_name && <div className="field-error">{validationErrors.first_name}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="last_name">Last Name:</label>
          <input type="text" id="last_name" name="last_name" value={person.last_name} onChange={handleInputChange} disabled={loading} />
           {validationErrors.last_name && <div className="field-error">{validationErrors.last_name}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="nickname">Nickname:</label>
          <input type="text" id="nickname" name="nickname" value={person.nickname} onChange={handleInputChange} disabled={loading} />
        </div>
        <div className="form-group">
          <label htmlFor="birth_date">Date of Birth:</label>
          <input type="date" id="birth_date" name="birth_date" value={person.birth_date} onChange={handleInputChange} disabled={loading} />
           {validationErrors.birth_date && <div className="field-error">{validationErrors.birth_date}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="place_of_birth">Place of Birth:</label>
          <input type="text" id="place_of_birth" name="place_of_birth" value={person.place_of_birth} onChange={handleInputChange} disabled={loading} />
        </div>
        <div className="form-group">
          <label htmlFor="death_date">Date of Death:</label>
          <input type="date" id="death_date" name="death_date" value={person.death_date} onChange={handleInputChange} disabled={loading} />
           {validationErrors.death_date && <div className="field-error">{validationErrors.death_date}</div>}
           {validationErrors.date_comparison && <div className="field-error">{validationErrors.date_comparison}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="place_of_death">Place of Death:</label>
          <input type="text" id="place_of_death" name="place_of_death" value={person.place_of_death} onChange={handleInputChange} disabled={loading} />
        </div>
        <div className="form-group">
          <label htmlFor="gender">Gender:</label>
          {/* Select uses global styles */}
          <select id="gender" name="gender" value={person.gender} onChange={handleInputChange} disabled={loading}>
            <option value="">-- Select Gender --</option> {/* Added empty option */}
            {validGenders.map(genderOption => (
                <option key={genderOption} value={genderOption}>{genderOption}</option>
            ))}
          </select>
           {validationErrors.gender && <div className="field-error">{validationErrors.gender}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="notes">Notes:</label>
          {/* Textarea uses global styles */}
          <textarea id="notes" name="notes" value={person.notes} onChange={handleInputChange} rows="4" disabled={loading} />
        </div>

        {/* Custom Attributes Section */}
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
                        disabled={loading}
                        style={{ width: '150px' }} // Adjust width for key input
                    />
                     <input
                        type="text"
                        placeholder="Attribute Value"
                        value={value}
                        onChange={(e) => handleAttributeChange({ target: { name: key, value: e.target.value } })}
                        disabled={loading}
                        style={{ flexGrow: 1 }} // Allow value input to take remaining space
                    />
                    <button type="button" onClick={() => removeCustomAttribute(key)} disabled={loading} style={{ width: 'auto', padding: '5px 10px', backgroundColor: 'var(--color-error-text)' }}>
                        Remove
                    </button>
                </div>
            ))}
            <button type="button" onClick={addCustomAttribute} disabled={loading} style={{ width: 'auto', marginTop: '10px', backgroundColor: 'var(--color-secondary)' }}>
                Add Attribute
            </button>
             {validationErrors.custom_attributes && <div className="field-error">{validationErrors.custom_attributes}</div>}
        </div>


        {/* Buttons use global styles */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem', justifyContent: 'flex-end' }}> {/* Align buttons to the right */}
            <Link to="/dashboard" className="button secondary-button"> {/* Use secondary-button class */}
                Cancel
            </Link>
            <button type="submit" disabled={loading}>
              {loading ? 'Adding...' : 'Add Person'}
            </button>
        </div>
      </form>
    </div>
  );
}

export default AddPersonPage;

