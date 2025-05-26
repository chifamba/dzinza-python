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
  const [loading, setLoading] = useState(true); // For initial load
  const containerRef = useRef(null);
  const { fitView } = useReactFlow();

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [totalPersons, setTotalPersons] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false); // For subsequent page loads

  // Layout calculation function - remains the same, processes given nodes/edges
  const calculateLayout = useCallback((rawNodes, rawEdges) => {
    // Ensure that the layout logic can handle nodes that might not have all their connections
    // if related nodes are on other pages. For initial load, this is fine.
    // The current layout seems to be a simple hierarchical one based on parent/child edges.
    // It might need adjustments if a more global layout considering all persons (even not yet loaded) is desired.
    // For now, we assume it lays out the provided subset of nodes.
    const nodeMap = new Map(rawNodes.map(node => [node.id, { ...node, children: [], parents: [] }]));
    
    rawEdges.forEach(edge => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source && target) {
        // Assuming 'parent' type edges define hierarchy for layout
        // Or adjust based on actual edge types used for layout ('customEdge' from backend)
        // If 'customEdge' implies parent-child, this logic might need to check edge.label or data
        // For simplicity, let's assume any edge means a connection for basic layout.
        // A more sophisticated layout might be needed for complex family trees.
        // This example assumes a simple top-down layout.
        source.children = source.children || [];
        target.parents = target.parents || [];
        source.children.push(target);
        target.parents.push(source);
      }
    });

    const rootNodes = Array.from(nodeMap.values()).filter(node => !node.parents || node.parents.length === 0);

    const assignPositions = (node, level = 0, horizontalOffset = 0, visited = new Set()) => {
      if (visited.has(node.id)) return; // Avoid cycles and redundant processing
      visited.add(node.id);

      node.position = { x: horizontalOffset, y: level * LEVEL_HEIGHT };
      
      const children = node.children || [];
      if (children.length > 0) {
        const childWidth = NODE_WIDTH * 1.5; // Spacing between children
        const totalChildWidth = children.length * childWidth;
        // Adjust startX to center children under parent, or align as preferred
        const startX = horizontalOffset - (totalChildWidth - childWidth) / 2;
        
        children.forEach((child, index) => {
          // Check if child exists in nodeMap (it should if it's from current page data)
          if (nodeMap.has(child.id)) {
            assignPositions(nodeMap.get(child.id), level + 1, startX + index * childWidth, visited);
          }
        });
      }
    };
    
    let currentXOffset = 0;
    rootNodes.forEach(root => {
      assignPositions(root, 0, currentXOffset, new Set());
      // Rough way to space out different root branches.
      // A more sophisticated algorithm would calculate the width of each branch.
      currentXOffset += NODE_WIDTH * 3; // Adjust as needed
    });

    return rawNodes.map(node => ({
      ...node,
      position: nodeMap.get(node.id)?.position || { x: Math.random() * 400, y: Math.random() * 400 }, // Fallback position
    }));
  }, []);

  useEffect(() => {
    const loadInitialTreeData = async () => {
      if (!activeTreeId) {
        setError('No active tree selected');
        setLoading(false);
        return;
      }

      try {
        setLoading(true); // For the initial load
        setError(null);
        // Fetch initial page (e.g., page 1, 10 items per page)
        const initialPage = 1;
        const itemsPerPage = 20; // Or a configurable value
        
        const response = await api.getTreeData(activeTreeId, initialPage, itemsPerPage);
        const { nodes: apiNodes, links: apiLinks, pagination } = response;
        
        const transformedNodes = apiNodes.map(node => ({
          ...node, // Contains id, type, data { id, label, full_name, ... }
          type: 'personNode', // Ensure type is set for custom node rendering
          data: { ...node.data, label: node.data.label || 'Unknown' }
        }));

        const transformedEdges = apiLinks.map(link => ({
          id: link.id,
          source: link.source,
          target: link.target,
          type: 'smoothstep', // Or link.type if provided by backend and matches React Flow types
          animated: false,
          style: { stroke: '#666', strokeWidth: 2 },
          data: link.data // Contains relationship type etc.
        }));

        const layoutedNodes = calculateLayout(transformedNodes, transformedEdges);
        
        setNodes(layoutedNodes);
        setEdges(transformedEdges);
        
        // Update pagination state
        setCurrentPage(pagination.current_page);
        setTotalPages(pagination.total_pages);
        setHasNextPage(pagination.has_next_page);
        setTotalPersons(pagination.total_items);
        
        setTimeout(() => {
          fitView({ padding: 0.2, duration: 300 });
        }, 100);

      } catch (err) {
        console.error('Failed to load initial tree data:', err);
        setError(err.message || 'Failed to load family tree data');
      } finally {
        setLoading(false);
      }
    };

    loadInitialTreeData();
  }, [activeTreeId, calculateLayout, fitView, setNodes, setEdges]); // Added setNodes, setEdges to dependencies

  const handleLoadMore = useCallback(async () => {
    if (!hasNextPage || loadingMore) return;

    setLoadingMore(true);
    setError(null); // Clear previous errors

    const nextPage = currentPage + 1;
    const itemsPerPage = 20; // Consistent with initial load, or from a config/state

    try {
      const response = await api.getTreeData(activeTreeId, nextPage, itemsPerPage);
      const { nodes: newApiNodes, links: newApiLinks, pagination } = response;

      const transformedNewNodes = newApiNodes.map(node => ({
        ...node,
        type: 'personNode',
        data: { ...node.data, label: node.data.label || 'Unknown' }
      }));

      const transformedNewEdges = newApiLinks.map(link => ({
        id: link.id, // Ensure unique IDs for edges too
        source: link.source,
        target: link.target,
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#666', strokeWidth: 2 },
        data: link.data
      }));

      // Combine existing nodes and edges with new ones
      // Ensure no duplicate nodes by checking IDs before adding
      const existingNodeIds = new Set(nodes.map(n => n.id));
      const uniqueNewNodes = transformedNewNodes.filter(n => !existingNodeIds.has(n.id));
      
      const combinedNodes = [...nodes, ...uniqueNewNodes];
      
      // Ensure no duplicate edges by checking IDs
      const existingEdgeIds = new Set(edges.map(e => e.id));
      const uniqueNewEdges = transformedNewEdges.filter(e => !existingEdgeIds.has(e.id));

      const combinedEdges = [...edges, ...uniqueNewEdges];
      
      const layoutedNodes = calculateLayout(combinedNodes, combinedEdges);
      
      setNodes(layoutedNodes);
      setEdges(combinedEdges); // Edges don't typically get new positions from layout function

      // Update pagination state from the new response
      setCurrentPage(pagination.current_page);
      setTotalPages(pagination.total_pages);
      setHasNextPage(pagination.has_next_page);
      // totalPersons remains the same as it's total for the tree

      // Optionally, fit view to include new nodes, or let user explore
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 300 });
      }, 100);

    } catch (err) {
      console.error('Failed to load more tree data:', err);
      setError(err.message || 'Failed to load more data. Please try again.');
      // Potentially revert currentPage if the load failed, or allow retry
    } finally {
      setLoadingMore(false);
    }
  }, [activeTreeId, currentPage, hasNextPage, loadingMore, nodes, edges, calculateLayout, fitView, setNodes, setEdges, setError, setCurrentPage, setTotalPages, setHasNextPage]);


  if (loading) { // This loading state is for the initial fetch
    return (
      <div className="flex justify-center items-center h-[600px] text-lg">
        Loading family tree visualization...
      </div>
    );
  }

  // Error display can be refined to show specific errors vs. general ones
  if (error && !loadingMore) { // Don't show main error overlay if just a load more error occurred, handle that inline
    return (
      <div className="p-4 text-red-600 bg-red-100 border border-red-400 rounded-md h-[600px]">
        <p className="font-semibold">Error loading visualization:</p>
        <p>{error}</p>
        {/* Optionally, provide a retry button for initial load failure */}
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col"> {/* Changed to full height and flex col */}
      <div ref={containerRef} className="flex-grow w-full h-[calc(100%-40px)] border border-gray-300 rounded-lg shadow-lg bg-white"> {/* Adjusted height */}
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
      <div className="h-[40px] flex justify-center items-center p-2">
        {hasNextPage && !loadingMore && (
          <button
            onClick={handleLoadMore}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
            disabled={loadingMore}
          >
            Load More People ({nodes.length}/{totalPersons})
          </button>
        )}
        {loadingMore && (
          <div className="text-sm text-gray-600">Loading more...</div>
        )}
        {!hasNextPage && nodes.length > 0 && nodes.length === totalPersons && (
           <div className="text-sm text-gray-500">All people loaded ({totalPersons}).</div>
        )}
         {error && loadingMore && ( // Display error specific to load more if it occurred
          <div className="text-sm text-red-500 ml-4">Error: {error}</div>
        )}
      </div>
    </div>
  );
};

FamilyTreeVisualization.propTypes = {
  activeTreeId: PropTypes.string.isRequired,
};

export default FamilyTreeVisualization;