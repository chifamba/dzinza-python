import React from 'react';
import { Handle, Position } from 'reactflow';

const PersonNode = ({ data }) => {
  const { name, birth_date } = data;
  return (
    <div style={{ border: '1px solid black', padding: '10px', borderRadius: '5px' }}>
      <Handle type="target" position={Position.Top} />
      <div>{name}</div><div>{birth_date}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default PersonNode;