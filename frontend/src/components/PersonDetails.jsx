import React, { useState, useEffect } from 'react';
import api from '../api';
import { Link } from 'react-router-dom'; // Import Link for the edit button

// Removed inline style imports if using global CSS

// Receive activeTreeId as a prop
const PersonDetails = ({ selectedPerson, people, activeTreeId }) => {
  const [personDetails, setPersonDetails] = useState(null);
  const [relatedInfo, setRelatedInfo] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchPersonDetails = async () => {
      if (!selectedPerson || !activeTreeId) { // Ensure activeTreeId is available
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
        // Fetch specific person details using their ID and the activeTreeId (implicitly via session)
        const personData = await api.getPerson(selectedPerson.person_id || selectedPerson.id, activeTreeId);
        // Fetch all relationships for the active tree (api.getAllRelationships uses session active_tree_id)
        const allRelationshipsData = await api.getAllRelationships(activeTreeId);

        if (isMounted) {
            setPersonDetails(personData);

            const currentPersonId = personData.id; // Use the ID from the fetched personData
            const relevantRelationships = allRelationshipsData.filter(
              // Filter relationships where the current person is either person1 or person2
              (rel) => rel.person1_id === currentPersonId || rel.person2_id === currentPersonId
            );

            const relatedInfoWithNames = relevantRelationships.map(rel => {
                // Determine the ID of the other person in the relationship
                const otherPersonId = rel.person1_id === currentPersonId ? rel.person2_id : rel.person1_id;
                // Find the other person's details from the 'people' array passed as a prop
                // The 'people' prop should contain all people in the currently active tree visualization
                const otherPerson = people?.find(p => p.person_id === otherPersonId);
                const otherPersonName = otherPerson ? `${otherPerson.first_name || ''} ${otherPerson.last_name || ''}`.trim() : `ID: ${otherPersonId?.substring(0, 8) || 'Unknown'}...`; // Handle missing otherPerson or ID

                return {
                     id: rel.id, // Use relationship ID
                     type: rel.relationship_type, // Use relationship_type from backend
                     otherPersonName: otherPersonName || 'Unknown', // Handle empty names
                     otherPersonId: otherPersonId
                };
            });
            setRelatedInfo(relatedInfoWithNames);
        }

      } catch (err) {
          if(isMounted){
            // Improve error message based on response if available
            const errorMsg = err.response?.data?.message || err.message || 'Failed to load person details or relationships.';
            setError({ type: 'fetch', message: errorMsg });
          }
        console.error('Error fetching person details:', err.response || err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchPersonDetails();
    // Dependencies: selectedPerson (to know which person to fetch), people (to find related names), activeTreeId (context for API calls)
    return () => { isMounted = false; };
  }, [selectedPerson, people, activeTreeId]); // Dependencies

  // Date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return 'N/A';
     try {
         // Assuming dateString is in ISO format (e.g., "YYYY-MM-DDTHH:mm:ss.sssZ" or "YYYY-MM-DD")
         return dateString.split('T')[0];
     } catch {
         return dateString; // Return original if parsing fails
     }
  };

  // Use CSS classes defined in index.css or a dedicated CSS module
  if (!selectedPerson) {
    return <div className="card">Select a person in the tree to view details.</div>;
  }

  if (loading) {
    return <div className="card">Loading details...</div>;
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
      {personDetails.nickname && <p><strong>Nickname:</strong> {personDetails.nickname}</p>}
      {/* Use strong tags for labels for better readability */}
      <p><strong>Born:</strong> {formatDate(personDetails.birth_date)} {personDetails.birth_place ? `in ${personDetails.birth_place}` : ''}</p>
      {personDetails.death_date && <p><strong>Died:</strong> {formatDate(personDetails.death_date)} {personDetails.death_place ? `in ${personDetails.death_place}` : ''}</p>}
      <p><strong>Gender:</strong> {personDetails.gender || 'N/A'}</p>
      {personDetails.is_living !== null && <p><strong>Living:</strong> {personDetails.is_living ? 'Yes' : 'No'}</p>} {/* Display is_living */}
      {personDetails.notes && <p><strong>Notes:</strong> {personDetails.notes}</p>}
      {/* Display custom attributes */}
      {personDetails.custom_attributes && Object.keys(personDetails.custom_attributes).length > 0 && (
          <>
              <h3 style={{ marginTop: '15px', marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px' }}>Custom Attributes:</h3>
              <ul style={{ paddingLeft: '20px', listStyle: 'disc', margin: 0 }}>
                  {Object.entries(personDetails.custom_attributes).map(([key, value]) => (
                      <li key={key} style={{ marginBottom: '3px' }}><strong>{key}:</strong> {String(value)}</li>
                  ))}
              </ul>
          </>
      )}

      <h3 style={{ marginTop: '15px', marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px' }}>
          Relationships:
      </h3>
      {relatedInfo.length === 0 ? (
        <p>No relationships found.</p>
      ) : (
        <ul style={{ paddingLeft: '20px', listStyle: 'disc', margin: 0 }}>
          {relatedInfo.map((rel) => (
            // Link to edit relationship page (requires implementing EditRelationshipPage)
            <li key={rel.id} style={{ marginBottom: '3px' }}>
                {rel.type} - {rel.otherPersonName}
                {/* Optional: Add edit button for relationship */}
                {/* <Link to={`/edit-relationship/${rel.id}`} style={{ marginLeft: '10px', fontSize: '0.8em' }}>Edit</Link> */}
            </li>
          ))}
        </ul>
      )}
       {/* Link to edit person page */}
       {personDetails.id && (
           <div style={{ marginTop: '20px', textAlign: 'center' }}>
               <Link to={`/edit-person/${personDetails.id}`} className="button">Edit Person</Link>
           </div>
       )}
    </div>
  );
};

export default PersonDetails;
