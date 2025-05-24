import React, { useEffect, useRef, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import ReactFlow, { 
  ReactFlowProvider, 
  useNodesState, 
  useEdgesState,
  Controls,
  Background,
  useReactFlow
} from 'reactflow';
import 'reactflow/dist/style.css';
import api from '../api';
import PersonNode from './PersonNode';

// Define custom node types
const nodeTypes = {
  personNode: PersonNode,
};

// Layout configuration
const LEVEL_HEIGHT = 100;
const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;

const FamilyTreeVisualization = ({ activeTreeId }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef(null);
  const { fitView } = useReactFlow();

  // Layout calculation function
  const calculateLayout = useCallback((rawNodes, rawEdges) => {
    const nodeMap = new Map(rawNodes.map(node => [node.id, { ...node, children: [], parents: [] }]));
    
    // Build parent-child relationships
    rawEdges.forEach(edge => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source && target) {
        if (edge.type === 'parent') {
          source.children.push(target);
          target.parents.push(source);
        }
      }
    });

    // Find root nodes (nodes without parents)
    const rootNodes = Array.from(nodeMap.values()).filter(node => node.parents.length === 0);

    // Assign levels and positions
    const assignPositions = (node, level = 0, horizontalOffset = 0) => {
      const y = level * LEVEL_HEIGHT;
      const x = horizontalOffset;
      
      node.position = { x, y };
      
      if (node.children.length > 0) {
        const childWidth = NODE_WIDTH * 1.5;
        const startX = x - ((node.children.length - 1) * childWidth) / 2;
        
        node.children.forEach((child, index) => {
          assignPositions(child, level + 1, startX + index * childWidth);
        });
      }
    };

    // Position all root nodes
    rootNodes.forEach((root, index) => {
      assignPositions(root, 0, index * NODE_WIDTH * 2);
    });

    // Update nodes with new positions
    const positionedNodes = rawNodes.map(node => ({
      ...node,
      position: nodeMap.get(node.id).position,
    }));

    return positionedNodes;
  }, []);

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
        
        // Transform nodes for ReactFlow
        const transformedNodes = apiNodes.map(node => ({
          ...node,
          type: 'personNode',
          data: {
            ...node.data,
            label: node.data.label || 'Unknown'
          }
        }));

        // Transform edges for ReactFlow
        const transformedEdges = links.map(link => ({
          id: link.id,
          source: link.source,
          target: link.target,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#666', strokeWidth: 2 },
          data: link.data
        }));

        // Apply layout
        const layoutedNodes = calculateLayout(transformedNodes, transformedEdges);
        
        setNodes(layoutedNodes);
        setEdges(transformedEdges);
        
        // Fit view after a short delay to ensure rendering is complete
        setTimeout(() => {
          fitView({ padding: 0.2 });
        }, 100);
      } catch (err) {
        console.error('Failed to load tree data:', err);
        setError(err.message || 'Failed to load family tree data');
      } finally {
        setLoading(false);
      }
    };

    loadTreeData();
  }, [activeTreeId, calculateLayout, fitView]);

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
    <div ref={containerRef} className="w-full h-[600px] border border-gray-300 rounded-lg shadow-lg bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-right"
        minZoom={0.1}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Controls />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
};

FamilyTreeVisualization.propTypes = {
  activeTreeId: PropTypes.string.isRequired,
};

export default FamilyTreeVisualization;