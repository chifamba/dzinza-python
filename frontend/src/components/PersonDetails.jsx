import React, { useState, useEffect } from 'react';
import { getPerson, getRelationships } from '../api';
import './PersonDetails.css';

const PersonDetails = ({ selectedPerson }) => {
  const [person, setPerson] = useState(null);
  const [relationships, setRelationships] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPersonDetails = async () => {
      if (!selectedPerson) {
        setPerson(null);
        setRelationships([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const personData = await getPerson(selectedPerson.id);
        const relationshipsData = await getRelationships();
        setPerson(personData);
        setRelationships(relationshipsData.filter((relationship) => relationship.person1 === selectedPerson.id || relationship.person2 === selectedPerson.id));
      } catch (err) {
        setError({ type: 'fetch', message: 'Failed to load person details.' });
        console.error('Error fetching person details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPersonDetails();
  }, [selectedPerson]);

  if (!selectedPerson) {
    return <div className="person-details-container">Select a person to view details.</div>;
  }

  if (loading) {
    return <div className="person-details-container">Loading...</div>;
  }

  if (error) {
    return <div className="person-details-container">Error: {error.message}</div>;
  }

  if (!person) {
    return <div className="person-details-container">Person details not found.</div>
  }

  return (<div className="person-details-container">
    <h2 className="person-name">{person.firstName} {person.lastName}</h2>
    <p>Born: {person.dateOfBirth}</p>
    {person.dateOfDeath && <p>Died: {person.dateOfDeath}</p>}
    <p>Gender: {person.gender}</p>
    <h3>Relationships:</h3>
    {relationships.length === 0 ? (
        <p>No relationships found.</p>
      ) : (
        <ul>
          {relationships.map((rel) => (
            <li key={rel.id}>{rel.relationshipType} - {rel.person1} and {rel.person2}</li>
          ))}
        </ul>
      )}
  </div>);
};

export default PersonDetails;
