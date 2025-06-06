import React, { memo, FC } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

// Data structure expected by this custom node
export interface PersonNodeData {
  name: string;
  birthDate?: string;
  deathDate?: string;
  photoUrl?: string; // URL to an image
  // Add other fields as needed, e.g., gender, occupation
}

const CustomPersonNode: FC<NodeProps<PersonNodeData>> = ({ data, isConnectable, selected }) => {
  const cardStyle: React.CSSProperties = {
    padding: '10px 15px',
    borderRadius: '8px',
    border: `2px solid ${selected ? '#007bff' : '#ddd'}`, // Highlight if selected
    backgroundColor: '#fff',
    fontFamily: 'Arial, sans-serif',
    fontSize: '12px',
    width: 180, // Fixed width for consistency
    boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
  };

  const photoStyle: React.CSSProperties = {
    width: 50,
    height: 50,
    borderRadius: '50%', // Circular photo
    objectFit: 'cover',
    backgroundColor: '#eee', // Placeholder background
    marginRight: '10px',
    float: 'left',
  };

  const nameStyle: React.CSSProperties = {
    fontWeight: 'bold',
    fontSize: '14px',
    marginBottom: '5px',
    color: '#333',
  };

  const dateStyle: React.CSSProperties = {
    fontSize: '10px',
    color: '#666',
    marginBottom: '3px',
  };

  const infoContainerStyle: React.CSSProperties = {
    marginLeft: 60, // Space for the photo
  };

  const dates = [];
  if (data.birthDate) dates.push(`B: ${data.birthDate}`);
  if (data.deathDate) dates.push(`D: ${data.deathDate}`);

  return (
    <div style={cardStyle}>
      {/* Handles for connecting edges */}
      {/* Allow connections from/to any side for flexibility */}
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} />
      <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} />
      <Handle type="target" position={Position.Left} isConnectable={isConnectable} />
      <Handle type="source" position={Position.Right} isConnectable={isConnectable} />

      <div>
        {data.photoUrl ? (
          <img src={data.photoUrl} alt={data.name} style={photoStyle} />
        ) : (
          <div style={photoStyle} /> // Placeholder div if no photo
        )}
        <div style={infoContainerStyle}>
          <div style={nameStyle}>{data.name || 'N/A'}</div>
          {dates.length > 0 && <div style={dateStyle}>{dates.join(' | ')}</div>}
          {/* Add more details here if needed */}
        </div>
      </div>
    </div>
  );
};

// Use memo for performance optimization, especially with many nodes
export default memo(CustomPersonNode);
