import React, { useState, useEffect } from 'react';
// Correctly import from default export 'api'
import api from '../api';
import './PersonDetails.css';

const PersonDetails = ({ selectedPerson, people }) => { // Added people prop
  const [personDetails, setPersonDetails] = useState(null); // Renamed state variable
  const [relatedInfo, setRelatedInfo] = useState([]); // Renamed state variable
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPersonDetails = async () => {
      if (!selectedPerson) {
        setPersonDetails(null);
        setRelatedInfo([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        // Fetch specific person details (optional if selectedPerson already has enough data)
        const personData = await api.getPerson(selectedPerson.id);
        setPersonDetails(personData);

        // Fetch all relationships to filter relevant ones
        const allRelationshipsData = await api.getAllRelationships(); // Corrected API call
        const relevantRelationships = allRelationshipsData.filter(
          (rel) => rel.person1_id === selectedPerson.id || rel.person2_id === selectedPerson.id
        );

        // Prepare related info with names
        const relatedInfoWithNames = relevantRelationships.map(rel => {
            const otherPersonId = rel.person1_id === selectedPerson.id ? rel.person2_id : rel.person1_id;
            // Find the other person's name from the passed 'people' prop or fetch if needed
            const otherPerson = people?.find(p => p.id === otherPersonId); // Use optional chaining
            const otherPersonName = otherPerson ? `${otherPerson.firstName} ${otherPerson.lastName}` : `ID: ${otherPersonId.substring(0, 8)}...`;
            return {
                 id: rel.id, // Assuming relationship has an ID
                 type: rel.rel_type,
                 otherPersonName: otherPersonName,
                 otherPersonId: otherPersonId
            };
        });
        setRelatedInfo(relatedInfoWithNames);

      } catch (err) {
        setError({ type: 'fetch', message: 'Failed to load person details or relationships.' });
        console.error('Error fetching person details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchPersonDetails();
    // Added 'people' to dependency array if it's expected to change
  }, [selectedPerson, people]);

  if (!selectedPerson) {
    return <div className="person-details-container">Select a person to view details.</div>;
  }

  if (loading) {
    return <div className="person-details-container">Loading...</div>;
  }

  if (error) {
    return <div className="person-details-container">Error: {error.message}</div>;
  }

  if (!personDetails) { // Check the renamed state variable
    return <div className="person-details-container">Person details not found.</div>;
  }

  // Basic date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return 'N/A';
     try {
         return dateString.split('T')[0];
     } catch {
         return dateString;
     }
  };

  return (
    <div className="person-details-container">
      <h2 className="person-name">{personDetails.first_name} {personDetails.last_name}</h2>
      {personDetails.nickname && <p>Nickname: {personDetails.nickname}</p>}
      <p>Born: {formatDate(personDetails.birth_date)} {personDetails.place_of_birth ? `in ${personDetails.place_of_birth}` : ''}</p>
      {personDetails.death_date && <p>Died: {formatDate(personDetails.death_date)} {personDetails.place_of_death ? `in ${personDetails.place_of_death}` : ''}</p>}
      <p>Gender: {personDetails.gender || 'N/A'}</p>
       {personDetails.notes && <p>Notes: {personDetails.notes}</p>}
      <h3>Relationships:</h3>
      {relatedInfo.length === 0 ? ( // Check the renamed state variable
        <p>No relationships found.</p>
      ) : (
        <ul>
          {/* Use the processed relatedInfo with names */}
          {relatedInfo.map((rel) => (
            <li key={rel.id}>{rel.type} - {rel.otherPersonName}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default PersonDetails;