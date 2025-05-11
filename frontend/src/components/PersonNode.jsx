import React from 'react';
import { Handle, Position } from 'reactflow';
import { useNavigate } from 'react-router-dom';

// --- IMPORT THE DEFAULT IMAGE ---
// Adjust the path based on the actual location relative to this file
// Assuming PersonNode.jsx is in src/components/
import defaultAvatar from '../assets/profiles/images/default_avatar.png'; // Adjust filename if needed

// Define CSS classes for the node elements (using template literal for multiline)
// Moved styles to index.css for better global management
// const nodeStyles = ` ... `;
// Inject styles into the head (simple approach) - Removed as styles are now in index.css
// const styleSheetExists = document.getElementById('person-node-styles');
// if (!styleSheetExists) { ... }


const PersonNode = ({ data, isConnectable }) => {
  const navigate = useNavigate();

  const handleEditClick = (e) => {
    e.stopPropagation(); // Prevent node click event when clicking button
    if (data?.id) {
      navigate(`/edit-person/${data.id}`);
    } else {
      console.error("PersonNode: Missing ID in node data", data);
    }
  };

  // Date formatting helper
  const formatDate = (dateString) => {
     if (!dateString) return '?';
     try {
          // Assuming dateString is in ISO format (e.g., "YYYY-MM-DDTHH:mm:ss.sssZ" or "YYYY-MM-DD")
          return dateString.split('T')[0];
     } catch {
          return dateString; // Return original if parsing fails
     }
  };

  // Use the imported default image variable
  // Assuming photoUrl is available in data if the backend supports it
  const imageUrl = data?.photoUrl || defaultAvatar;

  // Error handler for the image tag
  const handleImageError = (e) => {
      // Prevent infinite loop if the default avatar itself fails
      if (e.target.src !== defaultAvatar) {
          console.warn(`Failed to load image: ${data?.photoUrl}. Falling back to default.`);
          e.target.src = defaultAvatar;
      } else {
          console.error("Failed to load default avatar image.");
          // Optional: Hide image or show placeholder text/icon on default failure
          // e.target.style.display = 'none';
      }
  };

  return (
    // Use the CSS class defined in index.css
    <div className="person-node-container">
      {/* Handles for connecting edges */}
      <Handle type="target" position={Position.Top} id="top" isConnectable={isConnectable} />
      <div className="person-node-content">
        {/* Person Image */}
        <img
             // Use the determined image URL
             src={imageUrl}
             alt={data?.label || 'Profile'}
             className="person-node-image"
             // Use the error handler
             onError={handleImageError}
        />
        {/* Person Name */}
        <h3 className="person-node-name">{data?.label || 'Unnamed'}</h3>
        {/* Birth and Death Dates */}
        {(data?.dob || data?.dod) && (
            <p className="person-node-dates">
                ({formatDate(data.dob)} - {formatDate(data.dod)})
            </p>
        )}
        {/* Edit Button */}
        <button onClick={handleEditClick} className="person-node-edit-button">
             Edit
        </button>
      </div>
      {/* Handles for connecting edges */}
      <Handle type="source" position={Position.Bottom} id="bottom" isConnectable={isConnectable} />
    </div>
  );
};

export default PersonNode;
