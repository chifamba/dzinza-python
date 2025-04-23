import React, { useState } from 'react';
import api from '../api'; // Ensure path is correct
import { Link } from 'react-router-dom'; // Import Link for Cancel

function AddPersonPage() {
  const initialPersonState = {
      first_name: '', last_name: '', nickname: '',
      birth_date: '', death_date: '', // Use empty string for date inputs
      place_of_birth: '', place_of_death: '',
      gender: 'Male', notes: ''
  };
  const [person, setPerson] = useState(initialPersonState);
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson({ ...person, [name]: value });
     if (validationErrors[name]) {
         setValidationErrors(prevErrors => ({ ...prevErrors, [name]: null }));
     }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    setValidationErrors({});

    const dataToSend = {
        ...person,
        birth_date: person.birth_date || null, // Send null if empty
        death_date: person.death_date || null, // Send null if empty
    };

    try {
      await api.createPerson(dataToSend);
      setSuccessMessage('Person added successfully!');
      setPerson(initialPersonState); // Reset form
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
       const errorData = err.response?.data;
       let errorMsg = "Failed to add person.";
       if (errorData) {
           if (errorData.details && typeof errorData.details === 'object') {
                setValidationErrors(errorData.details);
                errorMsg = "Please correct the errors below.";
           } else { errorMsg = errorData.message || errorData.error || errorMsg; }
       } else { errorMsg = err.message || errorMsg; }
       setError(errorMsg);
       console.error("Add person error:", err.response || err);
    } finally {
      setLoading(false);
    }
  };

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
          <input type="text" id="first_name" name="first_name" value={person.first_name} onChange={handleInputChange} required />
           {validationErrors.first_name && <div className="field-error">{validationErrors.first_name}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="last_name">Last Name:</label>
          <input type="text" id="last_name" name="last_name" value={person.last_name} onChange={handleInputChange} />
           {validationErrors.last_name && <div className="field-error">{validationErrors.last_name}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="nickname">Nickname:</label>
          <input type="text" id="nickname" name="nickname" value={person.nickname} onChange={handleInputChange} />
        </div>
        <div className="form-group">
          <label htmlFor="birth_date">Date of Birth:</label>
          <input type="date" id="birth_date" name="birth_date" value={person.birth_date} onChange={handleInputChange} />
           {validationErrors.birth_date && <div className="field-error">{validationErrors.birth_date}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="place_of_birth">Place of Birth:</label>
          <input type="text" id="place_of_birth" name="place_of_birth" value={person.place_of_birth} onChange={handleInputChange} />
        </div>
        <div className="form-group">
          <label htmlFor="death_date">Date of Death:</label>
          <input type="date" id="death_date" name="death_date" value={person.death_date} onChange={handleInputChange} />
           {validationErrors.death_date && <div className="field-error">{validationErrors.death_date}</div>}
           {validationErrors.date_comparison && <div className="field-error">{validationErrors.date_comparison}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="place_of_death">Place of Death:</label>
          <input type="text" id="place_of_death" name="place_of_death" value={person.place_of_death} onChange={handleInputChange} />
        </div>
        <div className="form-group">
          <label htmlFor="gender">Gender:</label>
          {/* Select uses global styles */}
          <select id="gender" name="gender" value={person.gender} onChange={handleInputChange}>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
           {validationErrors.gender && <div className="field-error">{validationErrors.gender}</div>}
        </div>
         <div className="form-group">
          <label htmlFor="notes">Notes:</label>
          {/* Textarea uses global styles */}
          <textarea id="notes" name="notes" value={person.notes} onChange={handleInputChange} rows="4" />
        </div>
        {/* Buttons use global styles */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '1.5rem' }}> {/* Align buttons */}
            <button type="submit" disabled={loading}>
              {loading ? 'Adding...' : 'Add Person'}
            </button>
            <Link to="/dashboard" className="button" style={{ backgroundColor: 'var(--color-secondary)', textDecoration: 'none', textAlign: 'center' }}>
                Cancel
            </Link>
        </div>
      </form>
    </div>
  );
}

export default AddPersonPage;
