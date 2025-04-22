import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getPerson, updatePerson } from '../api';

function EditPersonPage({ personId }) {
  const [person, setPerson] = useState({ firstName: '', lastName: '', dateOfBirth: '', dateOfDeath: '', gender: '' });
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const { id } = useParams();

  useEffect(() => {
    const fetchPerson = async () => {
      try {
        const data = await getPerson(id);
        setPerson(data);
        if(data.gender !== "male" && data.gender !== "female"){
            setPerson({...data, gender: "male"})
        }
      } catch (err) {
        const error = err.message || "Failed to fetch person details"
        setError('Failed to fetch person details');
        console.error('Error fetching person:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPerson();
  }, [id]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setPerson({ ...person, [name]: value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
        await updatePerson(id, person);
        setSuccess(true);
        setError(null);
        setTimeout(() => {
          setSuccess(false);
        }, 3000);
    } catch (error) {
        if(error.response && error.response.status === 400){
            setError('Invalid data provided. Please check the form.');
        } else if (error.response && error.response.status === 404) {
            setError('The person you are trying to update could not be found');
        } else {
            setError('Failed to update person details.');
        }
        console.error('Error updating person:', error);
    }
    
    setLoading(false)
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div>
        {success && (
          <div style={{ color: 'green' }}>Person updated successfully!</div>
        )}
        {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      <h1>Edit Person</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="firstName">First Name:</label>
          <input type="text" id="firstName" name="firstName" value={person.firstName} onChange={handleInputChange} />
        </div>
        <div>
          <label htmlFor="lastName">Last Name:</label>
          <input type="text" id="lastName" name="lastName" value={person.lastName} onChange={handleInputChange}/>
        </div>
        <div>
          <label htmlFor="dateOfBirth">Date of Birth:</label>
          <input
            type="date"
            id="dateOfBirth"
            name="dateOfBirth"
            value={person.dateOfBirth}
            onChange={handleInputChange}
          />
        </div>
        <div>
          <label htmlFor="dateOfDeath">Date of Death:</label>
          <input
            type="date"
            id="dateOfDeath"
            name="dateOfDeath"
            value={person.dateOfDeath}
            onChange={handleInputChange}
          />
        </div>
        <div>
          <label htmlFor="gender">Gender:</label>
          <select id="gender" name="gender" value={person.gender} onChange={handleInputChange}>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
        <button type="submit" disabled={loading}>Save Changes</button>
      </form>
    </div>
  );
}

export default EditPersonPage;