import React from 'react';
import { Handle, Position } from 'reactflow';
import { useNavigate } from 'react-router-dom';

// --- IMPORT THE DEFAULT IMAGE ---
// Adjust the path based on the actual location relative to this file
// Assuming PersonNode.jsx is in src/components/
import defaultAvatar from '../assets/profiles/images/default_avatar.png'; // Adjust filename if needed

// Define CSS classes for the node elements (using template literal for multiline)
const nodeStyles = `
  .person-node-container {
    padding: 10px 15px;
    border: 1px solid var(--color-reactflow-node-border); /* Use CSS var */
    border-radius: 6px;
    background: var(--color-reactflow-node-bg); /* Use CSS var */
    color: var(--color-text); /* Use CSS var */
    text-align: center;
    min-width: 160px; /* Ensure minimum width */
    box-shadow: var(--box-shadow-sm);
    cursor: grab; /* Indicate draggable */
    transition: box-shadow 0.2s ease-in-out;
  }
  .person-node-container:hover {
      box-shadow: var(--box-shadow);
  }
  .person-node-content {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .person-node-image {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-bottom: 5px;
    border: 1px solid var(--color-border); /* Add subtle border */
    background-color: var(--color-secondary); /* Use secondary for placeholder bg */
    object-fit: cover; /* Ensure image covers the area */
  }
  .person-node-name {
    margin: 5px 0;
    font-size: 0.95em;
    font-weight: 600; /* Bold name */
  }
  .person-node-dates {
    margin: 2px 0;
    font-size: 0.8em;
    color: var(--color-secondary); /* Use secondary text color */
  }
  .person-node-edit-button {
    margin-top: 8px;
    font-size: 0.8em;
    padding: 3px 8px;
    background-color: var(--color-secondary); /* Use secondary button color */
    color: var(--color-button-text);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    opacity: 0.8;
    transition: opacity 0.2s ease-in-out, background-color 0.2s ease-in-out;
  }
  .person-node-edit-button:hover {
    background-color: var(--color-secondary-hover);
    opacity: 1;
  }
`;

// Inject styles into the head (simple approach)
// Consider CSS Modules or styled-components for larger apps
const styleSheetExists = document.getElementById('person-node-styles');
if (!styleSheetExists) {
    const styleSheet = document.createElement("style");
    styleSheet.id = 'person-node-styles'; // Add ID to prevent duplicates
    styleSheet.type = "text/css";
    styleSheet.innerText = nodeStyles;
    document.head.appendChild(styleSheet);
}


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
          return dateString.split('T')[0];
     } catch {
          return dateString;
     }
  };

  // Use the imported default image variable
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
    <div className="person-node-container">
      <Handle type="target" position={Position.Top} id="top" isConnectable={isConnectable} />
      <div className="person-node-content">
        <img
             // Use the determined image URL
             src={imageUrl}
             alt={data?.label || 'Profile'}
             className="person-node-image"
             // Use the error handler
             onError={handleImageError}
        />
        <h3 className="person-node-name">{data?.label || 'Unnamed'}</h3>
        {(data?.dob || data?.dod) && (
            <p className="person-node-dates">
                ({formatDate(data.dob)} - {formatDate(data.dod)})
            </p>
        )}
        <button onClick={handleEditClick} className="person-node-edit-button">
             Edit
        </button>
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" isConnectable={isConnectable} />
    </div>
  );
};

export default PersonNode;
