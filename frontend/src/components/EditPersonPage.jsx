import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom'; // Added Link
import api from '../api'; // Ensure this path is correct

function EditPersonPage() {
  // State for person data, loading, success, and error messages
  const [person, setPerson] = useState({
    first_name: '',
    last_name: '',
    nickname: '',
    birth_date: '',
    death_date: '',
    place_of_birth: '',
    place_of_death: '',
    gender: 'Male', // Default gender
    notes: ''
  });
  const [initialLoading, setInitialLoading] = useState(true); // For initial fetch
  const [saving, setSaving] = useState(false); // Separate state for saving operation
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({}); // For field-specific errors

  const navigate = useNavigate(); // Hook for navigation
  const { id } = useParams(); // Get person ID from URL parameter

  // Fetch person data when the component mounts or ID changes
  useEffect(() => {
    let isMounted = true; // Flag to prevent state update on unmounted component
    const fetchPerson = async () => {
      setInitialLoading(true);
      setError(null);
      setSuccess(false);
      setValidationErrors({});
      try {
        if (!id) {
          if (isMounted) setError('No person ID provided in URL.');
          if (isMounted) setInitialLoading(false);
          return;
        }
        // Fetch person data from API
        const data = await api.getPerson(id);
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
              gender: data.gender || 'Male',
              notes: data.notes || ''
            };
            setPerson(formattedData);
        }
      } catch (err) {
        // Handle fetch errors
        const errorMsg = err.response?.data?.message || err.message || "Failed to fetch person details";
        if (isMounted) setError(errorMsg);
        console.error('Error fetching person:', err);
      } finally {
        if (isMounted) setInitialLoading(false); // Loading finished
      }
    };

    fetchPerson();

    // Cleanup function to set isMounted to false when component unmounts
    return () => {
        isMounted = false;
    };
  }, [id]); // Re-run effect if the ID changes

  // Handle changes in form inputs
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson(prevPerson => ({ ...prevPerson, [name]: value }));
     // Clear validation error for this field when user types
     if (validationErrors[name]) {
         setValidationErrors(prevErrors => ({ ...prevErrors, [name]: null }));
     }
  };

  // Handle form submission
  const handleSubmit = async (event) => {
    event.preventDefault(); // Prevent default form submission
    setSaving(true); // Indicate saving state
    setError(null);
    setSuccess(false);
    setValidationErrors({}); // Clear previous validation errors

    // Prepare data for API (ensure dates are null if empty, otherwise keep YYYY-MM-DD)
    const dataToSend = {
      ...person,
      birth_date: person.birth_date || null,
      death_date: person.death_date || null,
    };

    try {
      // Send updated data to the API
      await api.updatePerson(id, dataToSend);
      setSuccess(true); // Show success message
      setError(null);
      // Optionally navigate back after a delay
      setTimeout(() => {
        setSuccess(false);
        // navigate('/dashboard'); // Example: navigate back to dashboard
      }, 3000);
    } catch (error) {
      // Handle submission errors
      const errorData = error.response?.data;
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
           errorMsg = error.message || errorMsg;
      }

      setError(errorMsg); // Set general error message
      console.error('Error updating person:', error.response || error);
    } finally {
      setSaving(false); // Saving finished
    }
  };

  // Style object for basic layout (consider using CSS classes)
  const styles = {
      container: { maxWidth: '600px', margin: '20px auto', padding: '20px', border: '1px solid #eee', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' },
      formGroup: { marginBottom: '15px' },
      label: { display: 'block', marginBottom: '5px', fontWeight: 'bold' },
      input: { width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box' },
      textarea: { width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box', minHeight: '80px' },
      select: { width: '100%', padding: '10px', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box', backgroundColor: 'white' },
      button: { padding: '10px 20px', border: 'none', borderRadius: '4px', backgroundColor: '#28a745', color: 'white', cursor: 'pointer', fontSize: '1em', marginRight: '10px' },
      buttonDisabled: { backgroundColor: '#aaa', cursor: 'not-allowed' },
      errorMessage: { color: 'red', marginBottom: '15px', padding: '10px', border: '1px solid red', borderRadius: '4px', backgroundColor: '#f8d7da' },
      fieldError: { color: 'red', fontSize: '0.9em', marginTop: '3px' },
      successMessage: { color: 'green', marginBottom: '15px', padding: '10px', border: '1px solid green', borderRadius: '4px', backgroundColor: '#d4edda' },
      link: { color: '#007bff', textDecoration: 'none' },
      actions: { marginTop: '20px' }
  };


  // Display loading indicator during initial fetch
  if (initialLoading) {
    return <div style={styles.container}>Loading person details...</div>;
  }

  // Display error if initial fetch failed significantly
  if (error && !person.first_name && !initialLoading) {
       return <div style={{...styles.container, ...styles.errorMessage}}>Error loading details: {error}</div>;
  }

  // Render the form
  return (
    <div style={styles.container}>
      <h1>Edit Person: {person.first_name} {person.last_name}</h1>
      {/* Display general error messages */}
      {error && <div style={styles.errorMessage}>{error}</div>}
      {/* Display success message */}
      {success && <div style={styles.successMessage}>Person updated successfully!</div>}

      <form onSubmit={handleSubmit}>
        {/* Form fields for person details */}
        <div style={styles.formGroup}>
          <label htmlFor="first_name" style={styles.label}>First Name:</label>
          <input type="text" id="first_name" name="first_name" style={styles.input} value={person.first_name} onChange={handleInputChange} required />
           {validationErrors.first_name && <div style={styles.fieldError}>{validationErrors.first_name}</div>}
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="last_name" style={styles.label}>Last Name:</label>
          <input type="text" id="last_name" name="last_name" style={styles.input} value={person.last_name} onChange={handleInputChange} />
           {validationErrors.last_name && <div style={styles.fieldError}>{validationErrors.last_name}</div>}
        </div>
         <div style={styles.formGroup}>
          <label htmlFor="nickname" style={styles.label}>Nickname:</label>
          <input type="text" id="nickname" name="nickname" style={styles.input} value={person.nickname} onChange={handleInputChange} />
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="birth_date" style={styles.label}>Date of Birth:</label>
          <input type="date" id="birth_date" name="birth_date" style={styles.input} value={person.birth_date} onChange={handleInputChange} />
           {validationErrors.birth_date && <div style={styles.fieldError}>{validationErrors.birth_date}</div>}
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="place_of_birth" style={styles.label}>Place of Birth:</label>
          <input type="text" id="place_of_birth" name="place_of_birth" style={styles.input} value={person.place_of_birth} onChange={handleInputChange} />
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="death_date" style={styles.label}>Date of Death:</label>
          <input type="date" id="death_date" name="death_date" style={styles.input} value={person.death_date} onChange={handleInputChange} />
           {validationErrors.death_date && <div style={styles.fieldError}>{validationErrors.death_date}</div>}
           {validationErrors.date_comparison && <div style={styles.fieldError}>{validationErrors.date_comparison}</div>}
        </div>
         <div style={styles.formGroup}>
          <label htmlFor="place_of_death" style={styles.label}>Place of Death:</label>
          <input type="text" id="place_of_death" name="place_of_death" style={styles.input} value={person.place_of_death} onChange={handleInputChange} />
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="gender" style={styles.label}>Gender:</label>
          <select id="gender" name="gender" style={styles.select} value={person.gender} onChange={handleInputChange}>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
           {validationErrors.gender && <div style={styles.fieldError}>{validationErrors.gender}</div>}
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="notes" style={styles.label}>Notes:</label>
          <textarea id="notes" name="notes" style={styles.textarea} value={person.notes} onChange={handleInputChange} rows="4" />
        </div>

        {/* Submit button with disabled state during saving */}
        <div style={styles.actions}>
            <button
                type="submit"
                style={saving ? {...styles.button, ...styles.buttonDisabled} : styles.button}
                disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
             <Link to="/dashboard" style={{...styles.link, marginLeft: '10px'}}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}

export default EditPersonPage;
