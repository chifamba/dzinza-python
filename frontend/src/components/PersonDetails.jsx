import React, { useState, useEffect, useMemo } from 'react';
import api from '../api';
import { Link } from 'react-router-dom'; // Import Link for the edit button

// Receive selectedPerson (node data), allNodesData, and activeTreeId as props
const PersonDetails = ({ selectedPerson, allNodesData, activeTreeId, onPersonRemoved }) => {
  // No need for separate personDetails state if selectedPerson has all info
  // const [personDetails, setPersonDetails] = useState(null);
  const [relatedInfo, setRelatedInfo] = useState([]);
  const [loadingRelationships, setLoadingRelationships] = useState(false);
  const [error, setError] = useState(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

  // Memoize the selected person's full details to avoid re-renders if the object reference changes but content is same
  const personDetails = useMemo(() => selectedPerson, [selectedPerson]);

  // Fetch relationships when selectedPerson or activeTreeId changes
  useEffect(() => {
    let isMounted = true;
    const fetchRelationships = async () => {
      // Ensure we have a selected person and an active tree
      if (!personDetails || !personDetails.id || !activeTreeId) {
        if (isMounted) {
            setRelatedInfo([]); // Clear related info if no person selected
            setError(null); // Clear errors
        }
        return;
      }

      if (isMounted) {
          setLoadingRelationships(true);
          setError(null);
      }

      try {
        // Fetch all relationships for the active tree
        // We need the full list to find relationships involving the selected person
        const allRelationshipsData = await api.getAllRelationships(activeTreeId);

        if (isMounted) {
            const currentPersonId = personDetails.id; // Use the ID from the selected person data
            const relevantRelationships = allRelationshipsData.filter(
              // Filter relationships where the current person is either person1 or person2
              (rel) => rel.person1_id === currentPersonId || rel.person2_id === currentPersonId
            );

            // Map relationships to include the name of the *other* person
            const relatedInfoWithNames = relevantRelationships.map(rel => {
                // Determine the ID of the other person in the relationship
                const otherPersonId = rel.person1_id === currentPersonId ? rel.person2_id : rel.person1_id;

                // Find the other person's details from the 'allNodesData' array passed as a prop
                // allNodesData contains the 'data' part of each node fetched by FamilyTreeVisualization
                const otherPersonNodeData = allNodesData?.find(p => p.id === otherPersonId);
                // Use the label or construct name from node data
                const otherPersonName = otherPersonNodeData?.label || `ID: ${otherPersonId?.substring(0, 8) || 'Unknown'}...`;

                return {
                     id: rel.id || `rel-${rel.person1_id}-${rel.person2_id}`, // Use relationship ID or generate one
                     type: rel.relationship_type, // Use relationship_type from backend
                     otherPersonName: otherPersonName || 'Unknown', // Handle empty names
                     otherPersonId: otherPersonId
                };
            });
            setRelatedInfo(relatedInfoWithNames);
        }

      } catch (err) {
          if(isMounted){
            const errorMsg = err.response?.data?.message || err.message || 'Failed to load relationships.';
            setError(errorMsg); // Set error state
            setRelatedInfo([]); // Clear related info on error
          }
        console.error('Error fetching relationships for details:', err.response || err);
      } finally {
        if (isMounted) setLoadingRelationships(false);
      }
    };

    fetchRelationships();
    // Dependencies: personDetails object (to trigger refetch when selection changes), activeTreeId
    return () => { isMounted = false; };
  }, [personDetails, activeTreeId, allNodesData]); // Include allNodesData as dependency

  // Date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return 'N/A';
     try {
         // Assuming dateString is in ISO format (e.g., "YYYY-MM-DDTHH:mm:ss.sssZ" or "YYYY-MM-DD")
         const datePart = dateString.split('T')[0];
         // Optional: Validate YYYY-MM-DD format
         if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
             return datePart;
         }
         return dateString; // Return original if not YYYY-MM-DD
     } catch {
         return dateString; // Return original if parsing fails
     }
  };

  // Function to handle removing a person from the current tree
  const handleRemoveFromTree = async () => {
    if (!personDetails?.id || !activeTreeId) return;
    
    setIsRemoving(true);
    setError(null);
    
    try {
      await api.removePersonFromTree(personDetails.id, activeTreeId);
      setShowRemoveConfirm(false);
      // Call the callback to notify parent component
      if (onPersonRemoved) {
        onPersonRemoved(personDetails.id);
      }
    } catch (err) {
      console.error("Failed to remove person from tree:", err);
      setError(err.response?.data?.message || err.message || "Failed to remove person from tree");
    } finally {
      setIsRemoving(false);
    }
  };

  // Use CSS classes defined in index.css or a dedicated CSS module
  if (!personDetails) {
    // Use card class for consistent styling
    return <div className="card">Select a person in the tree to view details.</div>;
  }

  // Display general error if one occurred during relationship fetch
   if (error) {
     return <div className="card message error-message">Error loading details: {error}</div>;
   }

  // Person details are available from the prop
  return (
    // Use card class for container styling
    <div className="card person-details-card"> {/* Add specific class if needed */}
      <h2 style={{ marginTop: 0, marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px', fontSize: '1.2rem' }}>
          {/* Use full_name if available, otherwise construct from node data */}
          {personDetails.full_name || `${personDetails.first_name || ''} ${personDetails.last_name || ''}`.trim() || personDetails.label || 'Unnamed'}
      </h2>
      {personDetails.nickname && <p><strong>Nickname:</strong> {personDetails.nickname}</p>}
      {/* Use strong tags for labels for better readability */}
      {/* Use dob/dod fields from node data */}
      <p><strong>Born:</strong> {formatDate(personDetails.dob)} {personDetails.birth_place ? `in ${personDetails.birth_place}` : ''}</p>
      {personDetails.dod && <p><strong>Died:</strong> {formatDate(personDetails.dod)} {personDetails.death_place ? `in ${personDetails.death_place}` : ''}</p>}
      <p><strong>Gender:</strong> {personDetails.gender || 'N/A'}</p>
      {/* Display is_living status from node data */}
      {personDetails.is_living !== null && typeof personDetails.is_living !== 'undefined' && (
          <p><strong>Living:</strong> {personDetails.is_living ? 'Yes' : 'No'}</p>
      )}
      {personDetails.notes && <p><strong>Notes:</strong> {personDetails.notes}</p>}

      {/* Display custom attributes if they exist in the node data */}
      {personDetails.custom_attributes && Object.keys(personDetails.custom_attributes).length > 0 && (
          <>
              <h3 style={{ marginTop: '15px', marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px', fontSize: '1.1rem' }}>Custom Attributes:</h3>
              <ul style={{ paddingLeft: '20px', listStyle: 'disc', margin: 0 }}>
                  {Object.entries(personDetails.custom_attributes).map(([key, value]) => (
                      <li key={key} style={{ marginBottom: '3px' }}><strong>{key}:</strong> {String(value)}</li>
                  ))}
              </ul>
          </>
      )}

      <h3 style={{ marginTop: '15px', marginBottom: '10px', borderBottom: '1px solid var(--color-border)', paddingBottom: '5px', fontSize: '1.1rem' }}>
          Relationships:
      </h3>
      {loadingRelationships ? (
          <p>Loading relationships...</p>
      ) : relatedInfo.length === 0 ? (
        <p>No relationships found.</p>
      ) : (
        <ul style={{ paddingLeft: '20px', listStyle: 'disc', margin: 0 }}>
          {relatedInfo.map((rel) => (
            // Link to edit relationship page (requires implementing EditRelationshipPage)
            <li key={rel.id} style={{ marginBottom: '3px' }}>
                {/* Display formatted relationship type */}
                {rel.type ? rel.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') : 'Related'} - {rel.otherPersonName}
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
               
               {/* Add button to remove person from tree */}
               {!showRemoveConfirm ? (
                 <button 
                   className="button button-danger" 
                   style={{ marginLeft: '10px' }}
                   onClick={() => setShowRemoveConfirm(true)}
                 >
                   Remove from Tree
                 </button>
               ) : (
                 <div style={{ marginTop: '10px', padding: '10px', border: '1px solid #ff6b6b', borderRadius: '4px', backgroundColor: '#fff0f0' }}>
                   <p style={{ marginBottom: '10px' }}>
                     Are you sure you want to remove this person from the current tree? 
                     The person record will remain in the system and can be added to this or other trees later.
                   </p>
                   <button 
                     className="button button-danger" 
                     disabled={isRemoving}
                     onClick={handleRemoveFromTree}
                   >
                     {isRemoving ? 'Removing...' : 'Confirm Remove'}
                   </button>
                   <button 
                     className="button" 
                     style={{ marginLeft: '10px' }}
                     disabled={isRemoving}
                     onClick={() => setShowRemoveConfirm(false)}
                   >
                     Cancel
                   </button>
                 </div>
               )}
           </div>
       )}
    </div>
  );
};

export default PersonDetails;
