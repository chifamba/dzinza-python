import React, { useState, useEffect } from 'react';
import api from '../api';
// Removed inline style imports if using global CSS

const PersonDetails = ({ selectedPerson, people }) => {
  const [personDetails, setPersonDetails] = useState(null);
  const [relatedInfo, setRelatedInfo] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchPersonDetails = async () => {
      if (!selectedPerson) {
        if (isMounted) {
            setPersonDetails(null);
            setRelatedInfo([]);
        }
        return;
      }
      if (isMounted) {
          setLoading(true);
          setError(null);
      }
      try {
        const personData = await api.getPerson(selectedPerson.person_id || selectedPerson.id); // Use correct ID key
        const allRelationshipsData = await api.getAllRelationships();

        if (isMounted) {
            setPersonDetails(personData);

            const currentPersonId = personData.person_id; // Use consistent ID
            const relevantRelationships = allRelationshipsData.filter(
              (rel) => rel.person1_id === currentPersonId || rel.person2_id === currentPersonId
            );

            const relatedInfoWithNames = relevantRelationships.map(rel => {
                const otherPersonId = rel.person1_id === currentPersonId ? rel.person2_id : rel.person1_id;
                const otherPerson = people?.find(p => p.person_id === otherPersonId);
                const otherPersonName = otherPerson ? `${otherPerson.first_name} ${otherPerson.last_name}`.trim() : `ID: ${otherPersonId.substring(0, 8)}...`;
                return {
                     id: rel.rel_id,
                     type: rel.rel_type,
                     otherPersonName: otherPersonName || 'Unknown', // Handle empty names
                     otherPersonId: otherPersonId
                };
            });
            setRelatedInfo(relatedInfoWithNames);
        }

      } catch (err) {
          if(isMounted){
            setError({ type: 'fetch', message: 'Failed to load person details or relationships.' });
          }
        console.error('Error fetching person details:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchPersonDetails();
    return () => { isMounted = false; };
  }, [selectedPerson, people]); // Dependencies

  // Date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return 'N/A';
     try {
         return dateString.split('T')[0];
     } catch {
         return dateString;
     }
  };

  // Use CSS classes defined in index.css or a dedicated CSS module
  if (!selectedPerson) {
    return <div className="card">Select a person to view details.</div>;
  }

  if (loading) {
    return <div className="card">Loading...</div>;
  }

  if (error) {
    return <div className="card message error-message">Error: {error.message}</div>;
  }

  if (!personDetails) {
    return <div className="card">Person details not found.</div>;
  }

  return (
    // Use card class for container styling
    <div className="card person-details-card"> {/* Add specific class if needed */}
      <h2 style={{ marginTop: 0, marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px' }}>
          {personDetails.first_name} {personDetails.last_name}
      </h2>
      {personDetails.nickname && <p>Nickname: {personDetails.nickname}</p>}
      <p>Born: {formatDate(personDetails.birth_date)} {personDetails.place_of_birth ? `in ${personDetails.place_of_birth}` : ''}</p>
      {personDetails.death_date && <p>Died: {formatDate(personDetails.death_date)} {personDetails.place_of_death ? `in ${personDetails.place_of_death}` : ''}</p>}
      <p>Gender: {personDetails.gender || 'N/A'}</p>
       {personDetails.notes && <p>Notes: {personDetails.notes}</p>}
      <h3 style={{ marginTop: '15px', marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px' }}>
          Relationships:
      </h3>
      {relatedInfo.length === 0 ? (
        <p>No relationships found.</p>
      ) : (
        <ul style={{ paddingLeft: '20px', listStyle: 'disc', margin: 0 }}>
          {relatedInfo.map((rel) => (
            <li key={rel.id} style={{ marginBottom: '3px' }}>{rel.type} - {rel.otherPersonName}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default PersonDetails;
