import React, { useState } from 'react';
import { addPerson } from '../api';

function AddPersonPage() {
  const [person, setPerson] = useState({ firstName: '', lastName: '', dateOfBirth: '', dateOfDeath: '', gender: 'male' });
  const [successMessage, setSuccessMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson({ ...person, [name]: value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await addPerson(person);
      setSuccessMessage('Person added successfully!');
      setPerson({ firstName: '', lastName: '', dateOfBirth: '', dateOfDeath: '', gender: 'male' });
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getErrorMessage = (error) => {
    if (!error) return null;
    return error;
  };

  return (
    <div>
      <h1>Add New Person</h1>
      {successMessage && <div className="success-message">{successMessage}</div>}
      {error && <div className="error-message">{getErrorMessage(error)}</div>}
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="firstName">First Name:</label>
          <input type="text" id="firstName" name="firstName" value={person.firstName} onChange={handleInputChange} required />
        </div>
        <div>
          <label htmlFor="lastName">Last Name:</label>
          <input type="text" id="lastName" name="lastName" value={person.lastName} onChange={handleInputChange} required />
        </div>
        <div>
          <label htmlFor="dateOfBirth">Date of Birth:</label>
          <input type="date" id="dateOfBirth" name="dateOfBirth" value={person.dateOfBirth} onChange={handleInputChange} />
        </div>
        <div>
          <label htmlFor="dateOfDeath">Date of Death:</label>
          <input type="date" id="dateOfDeath" name="dateOfDeath" value={person.dateOfDeath} onChange={handleInputChange} />
        </div>
        <div>
          <label htmlFor="gender">Gender:</label>
          <select id="gender" name="gender" value={person.gender} onChange={handleInputChange}>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Adding...' : 'Add Person'}
        </button>
      </form>
    </div>
  );
}

export default AddPersonPage;