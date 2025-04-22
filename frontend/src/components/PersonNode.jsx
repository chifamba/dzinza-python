--- a/frontend/src/components/PersonNode.jsx
+++ b/frontend/src/components/PersonNode.jsx

import React from 'react';
import { Handle, Position } from 'reactflow';
import { useNavigate } from 'react-router-dom';

const PersonNode = ({ data, isConnectable }) => {
  return (
    <div className="person-node">
      <Handle
        type="target"
        position="top"
        id="top"
        isConnectable={isConnectable}
      />
      <div className="person-node-content">
        <img src="/images/default.png" alt="Profile" className="person-node-image" />
        <h3>{data.label}</h3>
        <p>Born: {data.dateOfBirth}</p>
        <button onClick={() => navigate(`/edit-person/${data.id}`)}>Edit</button>
      </div>
      <Handle
        type="source"
        position="bottom"
        id="bottom"
        isConnectable={isConnectable}
      />
    </div>
  );
};

export default PersonNode;
