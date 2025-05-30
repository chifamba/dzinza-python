import React, { useEffect, useRef, useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import ReactFlow, { 
  ReactFlowProvider, 
  useNodesState, 
  useEdgesState,
  Controls,
  Background,
  useReactFlow,
  addEdge // Import addEdge utility
} from 'reactflow';
import 'reactflow/dist/style.css';
import api from '../api';
import PersonNode from './PersonNode';
import RelationshipTypeModal from './RelationshipTypeModal'; // Import the modal

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

  // Modal State
  const [isRelationshipModalOpen, setIsRelationshipModalOpen] = useState(false);
  const [connectionDetails, setConnectionDetails] = useState(null);

  // State to store page size from backend
  const [pageSize, setPageSize] = useState(20); // Default to 20 until we get config from backend


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
    const loadTreeData = async (page = 1) => {
      if (!activeTreeId) {
        setError('No active tree selected');
        setLoading(false);
        return;
      }

      try {
        setLoading(true); 
        setError(null);
        
        // Don't specify itemsPerPage (pass null) to use backend default
        const response = await api.getTreeData(activeTreeId, page, null);
        const { nodes: apiNodes, links: apiLinks, pagination } = response;
        
        // Store the page size from backend for future requests
        if (pagination && pagination.per_page) {
          setPageSize(pagination.per_page);
        }
        
        const transformedNodes = apiNodes.map(node => ({
          ...node,
          type: 'personNode',
          data: { ...node.data, label: node.data.label || 'Unknown' }
        }));

        const transformedEdges = apiLinks.map(link => ({
          id: link.id,
          source: link.source,
          target: link.target,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#666', strokeWidth: 2 },
          data: link.data
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
        console.error('Failed to load tree data:', err);
        setError(err.message || 'Failed to load family tree data');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    };

    loadTreeData();
  }, [activeTreeId, calculateLayout, fitView, setNodes, setEdges]);

  // Create navigation functions for next and previous page
  const loadPage = useCallback(async (page) => {
    if (loadingMore) return;

    setLoadingMore(true);
    setError(null);

    try {
      const response = await api.getTreeData(activeTreeId, page, pageSize);
      const { nodes: apiNodes, links: apiLinks, pagination } = response;

      const transformedNodes = apiNodes.map(node => ({
        ...node,
        type: 'personNode',
        data: { ...node.data, label: node.data.label || 'Unknown' }
      }));

      const transformedEdges = apiLinks.map(link => ({
        id: link.id,
        source: link.source,
        target: link.target,
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#666', strokeWidth: 2 },
        data: link.data
      }));

      // Replace current nodes and edges with new ones from this page
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
      console.error(`Failed to load page ${page}:`, err);
      setError(err.message || 'Failed to load page. Please try again.');
    } finally {
      setLoadingMore(false);
    }
  }, [activeTreeId, loadingMore, calculateLayout, fitView, pageSize]);

  const handleNextPage = useCallback(() => {
    if (hasNextPage && !loadingMore) {
      loadPage(currentPage + 1);
    }
  }, [currentPage, hasNextPage, loadingMore, loadPage]);

  const handlePrevPage = useCallback(() => {
    if (currentPage > 1 && !loadingMore) {
      loadPage(currentPage - 1);
    }
  }, [currentPage, loadingMore, loadPage]);

  const handleOnConnect = useCallback((params) => {
    // Find source and target node objects from the current 'nodes' state
    const sourceNode = nodes.find(node => node.id === params.source);
    const targetNode = nodes.find(node => node.id === params.target);

    if (sourceNode && targetNode) {
      setConnectionDetails({
        source: params.source,
        target: params.target,
        sourceHandle: params.sourceHandle,
        targetHandle: params.targetHandle,
        sourceNode: sourceNode, // Full source node object
        targetNode: targetNode, // Full target node object
      });
      setIsRelationshipModalOpen(true);
    } else {
      console.error("Could not find source or target node for connection:", params, nodes);
      // Optionally, provide user feedback here if nodes are not found
    }
  }, [nodes, setConnectionDetails, setIsRelationshipModalOpen]); // Added nodes dependency

  const handleCloseRelationshipModal = useCallback(() => {
    setIsRelationshipModalOpen(false);
    setConnectionDetails(null);
  }, [setIsRelationshipModalOpen, setConnectionDetails]);

  const handleSubmitRelationshipModal = useCallback(async (modalData) => {
    // modalData is { relationshipType: 'selected_type' }
    if (!connectionDetails) {
      console.error("No connection details available for submission.");
      handleCloseRelationshipModal();
      return;
    }

    const { source, target, sourceNode, targetNode } = connectionDetails;
    const { relationshipType } = modalData;

    // Payload for the API
    const relationshipPayload = {
      person1_id: source,
      person2_id: target,
      relationship_type: relationshipType,
      // start_date, end_date, notes can be added here if collected by the modal
    };

    // Clear previous general errors, specific errors handled below
    setError(null); 

    try {
      console.log('Attempting to create relationship with payload:', relationshipPayload);
      // The second argument to api.createRelationship is activeTreeId,
      // but it's not used by the current api.js implementation of createRelationship.
      // The backend endpoint /relationships (POST) relies on session for activeTreeId.
      const createdRelationship = await api.createRelationship(relationshipPayload, activeTreeId);
      
      console.log('Relationship created successfully:', createdRelationship);

      if (createdRelationship && createdRelationship.id) {
        const newEdge = {
          id: String(createdRelationship.id), // Ensure ID is a string
          source: String(createdRelationship.person1_id), // Ensure source/target are strings
          target: String(createdRelationship.person2_id),
          type: 'smoothstep', // Or your preferred edge type
          label: createdRelationship.relationship_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          data: { ...createdRelationship }, // Store full relationship data
        };
        setEdges((eds) => addEdge(newEdge, eds));
        // Optionally, add a success notification here
      } else {
        // This case might indicate an issue with the API response structure
        console.error("Created relationship data is missing ID or is invalid:", createdRelationship);
        setError("Failed to create relationship: Invalid response from server.");
      }
    } catch (apiError) {
      console.error("Failed to create relationship via API:", apiError);
      // Display error to the user. The existing error display logic will pick this up.
      setError(apiError.response?.data?.message || apiError.message || "An unknown error occurred while creating the relationship.");
      // No need to remove a temporary edge as we are not adding one optimistically anymore before API call.
    } finally {
      handleCloseRelationshipModal();
    }
  }, [connectionDetails, handleCloseRelationshipModal, setEdges, activeTreeId, setError]);


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
      <div ref={containerRef} className="flex-grow w-full h-[calc(100%-50px)] border border-gray-300 rounded-lg shadow-lg bg-white"> {/* Adjusted height */}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={handleOnConnect} // Added onConnect handler
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
      <div className="h-[50px] flex justify-center items-center p-2 gap-4">
        {/* Previous Page Button */}
        <button
          onClick={handlePrevPage}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          disabled={currentPage <= 1 || loadingMore}
        >
          Previous
        </button>

        {/* Page Indicator */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            Page {currentPage} of {totalPages || 1}
          </span>
          <span className="text-xs text-gray-500">
            ({nodes.length} of {totalPersons} people, {pageSize} per page)
          </span>
        </div>

        {/* Next Page Button */}
        <button
          onClick={handleNextPage}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          disabled={!hasNextPage || loadingMore}
        >
          Next
        </button>

        {/* Loading Indicator */}
        {loadingMore && (
          <div className="text-sm text-gray-600 ml-2">Loading...</div>
        )}

        {/* Error Display */}
        {error && (
          <div className="text-sm text-red-500 ml-2">Error: {error}</div>
        )}
      </div>

      {isRelationshipModalOpen && connectionDetails && (
        <RelationshipTypeModal
          isOpen={isRelationshipModalOpen}
          onClose={handleCloseRelationshipModal}
          onSubmit={handleSubmitRelationshipModal}
          sourceNode={connectionDetails.sourceNode}
          targetNode={connectionDetails.targetNode}
        />
      )}
    </div>
  );
};

FamilyTreeVisualization.propTypes = {
  activeTreeId: PropTypes.string.isRequired,
};

export default FamilyTreeVisualization;