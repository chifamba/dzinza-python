// src/components/FamilyTreeVisualization.jsx
import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import ReactFlow, { ReactFlowProvider } from 'reactflow';
import api from '../api';

const FamilyTreeVisualization = ({ activeTreeId }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef(null);

  useEffect(() => {
    const loadTreeData = async () => {
      if (!activeTreeId) {
        setError('No active tree selected');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const { nodes: apiNodes, links } = await api.getTreeData();
        
        // Transform nodes and edges for ReactFlow
        const transformedNodes = apiNodes.map(node => ({
          ...node,
          type: 'personNode', // Custom node type 
          data: {
            ...node.data,
            label: node.data.label || 'Unknown'
          }
        }));

        const transformedEdges = links.map(link => ({
          id: link.id,
          source: link.source,
          target: link.target,
          type: 'step',
          label: link.label,
          animated: false,
          data: link.data
        }));

        setNodes(transformedNodes);
        setEdges(transformedEdges);
      } catch (err) {
        console.error('Failed to load tree data:', err);
        setError(err.message || 'Failed to load family tree data');
      } finally {
        setLoading(false);
      }
    };

    loadTreeData();
  }, [activeTreeId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[600px] text-lg">
        Loading family tree visualization...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-600 bg-red-100 border border-red-400 rounded-md h-[600px]">
        <p className="font-semibold">Error loading visualization:</p>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="w-full h-[600px] border border-gray-300 rounded-lg shadow-lg bg-white"
    >
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          attributionPosition="bottom-right"
        />
      </ReactFlowProvider>
    </div>
  );
};

FamilyTreeVisualization.propTypes = {
  activeTreeId: PropTypes.string.isRequired,
};

export default FamilyTreeVisualization;
