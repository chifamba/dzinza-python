import React from 'react';
import { Handle, Position } from 'reactflow';
import { useNavigate } from 'react-router-dom'; // Keep import

const PersonNode = ({ data, isConnectable }) => {
  const navigate = useNavigate(); // Call hook at the top level

  const handleEditClick = () => {
    if (data?.id) {
      navigate(`/edit-person/${data.id}`); // Use the ID from node data
    } else {
      console.error("PersonNode: Missing ID in node data", data);
    }
  };

  // Basic date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return '?';
     try {
          // Assuming dateString is like "YYYY-MM-DD" or "YYYY-MM-DDTHH:mm:ss"
          return dateString.split('T')[0];
     } catch {
          return dateString; // Return original if formatting fails
     }
  };


  return (
    <div className="person-node" style={{ padding: '10px', border: '1px solid #ccc', borderRadius: '5px', background: '#fff', textAlign: 'center' }}>
      <Handle
        type="target"
        position={Position.Top} // Use Position enum
        id="top"
        isConnectable={isConnectable}
        style={{ background: '#555' }}
      />
      <div className="person-node-content">
        {/* Use photoUrl from data if available, otherwise default */}
        <img
             src={data.photoUrl || "/images/default.png"}
             alt={data.label || 'Profile'}
             className="person-node-image"
             style={{ width: '40px', height: '40px', borderRadius: '50%', marginBottom: '5px' }}
             onError={(e) => { e.target.src = '/images/default.png'; }} // Fallback image on error
        />
        <h3 style={{ margin: '5px 0', fontSize: '1em' }}>{data.label || 'Unnamed'}</h3>
         {/* Display DOB, DOD if available */}
        {data.dob && <p style={{ margin: '2px 0', fontSize: '0.8em' }}>Born: {formatDate(data.dob)}</p>}
        {data.dod && <p style={{ margin: '2px 0', fontSize: '0.8em' }}>Died: {formatDate(data.dod)}</p>}
        <button onClick={handleEditClick} style={{ marginTop: '5px', fontSize: '0.8em', padding: '2px 5px' }}>
             Edit
        </button>
      </div>
      <Handle
        type="source"
        position={Position.Bottom} // Use Position enum
        id="bottom"
        isConnectable={isConnectable}
        style={{ background: '#555' }}
      />
    </div>
  );
};

export default PersonNode;