import React, { useState, useEffect, useCallback, useRef } from 'react';
import dagre from 'dagre';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  MarkerType // Import MarkerType for edge arrows if needed
} from 'reactflow';
import 'reactflow/dist/style.css'; // Ensure styles are imported
import PersonDetails from './PersonDetails';
import PersonNode from './PersonNode'; // Ensure PersonNode uses CSS vars/classes
import api from '../api';
import { useAuth } from '../context/AuthContext'; // Import useAuth

// Define node types used in the flow
const nodeTypes = {
  personNode: PersonNode,
  // Add other custom node types if needed
};

// Layout constants
const nodeWidth = 172;
const nodeHeight = 80; // Adjust if PersonNode size changes
const spouseDummyNodeHeight = 20; // Small height for invisible nodes
const rankdir = 'TB'; // Top to Bottom ranking is standard for family trees

// Function to calculate layout using Dagre with dummy nodes for spouses
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  // Input validation
  if (!Array.isArray(nodes) || !Array.isArray(edges)) {
      console.error("Invalid input to getLayoutedElements: nodes and edges must be arrays.");
      return { nodes: [], edges: [] };
  }

  const dagreGraph = new dagre.graphlib.Graph({ compound: true }); // Use compound graph for potential grouping
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
      rankdir: direction,
      ranksep: 60, // Increase separation between ranks (generations)
      nodesep: 30, // Increase separation between nodes in the same rank
      align: 'UL', // Align nodes to upper-left in their rank cell
  });

  const spouseEdges = edges.filter(edge => edge.data?.rel_type?.toLowerCase() === 'spouse_current' || edge.data?.rel_type?.toLowerCase() === 'spouse_former' || edge.data?.rel_type?.toLowerCase() === 'partner');
  // Correctly identify parent/child edges based on relationship_type enum
  const parentChildEdges = edges.filter(edge => edge.data?.rel_type?.toLowerCase().includes('parent') || edge.data?.rel_type?.toLowerCase().includes('child'));
  const otherEdges = edges.filter(edge => !spouseEdges.includes(edge) && !parentChildEdges.includes(edge));

  const processedNodes = new Set(); // Keep track of nodes already added
  const dummyNodes = new Map(); // Store dummy nodes: key = sorted spouse IDs string, value = dummy node ID

  // 1. Add Person Nodes to Dagre Graph
  nodes.forEach((node) => {
    // Ensure node and node.id exist before setting
    if (node && node.id) {
        dagreGraph.setNode(node.id, { label: node.data?.label || node.id, width: nodeWidth, height: nodeHeight });
        processedNodes.add(node.id);
    } else {
        console.warn("Skipping invalid node in layout:", node);
    }
  });

  // 2. Process Spouse Relationships and Create Dummy Nodes
  spouseEdges.forEach((edge) => {
    // Ensure edge, source, and target exist
    if (!edge || !edge.source || !edge.target) {
        console.warn("Skipping invalid spouse edge in layout:", edge);
        return;
    }
    const sourceId = edge.source;
    const targetId = edge.target;
    const sortedIds = [sourceId, targetId].sort().join('-'); // Unique key for the pair
    let dummyNodeId;

    if (!dummyNodes.has(sortedIds)) {
        // Create a new dummy node for this spouse pair
        dummyNodeId = `dummy-${sortedIds}`;
        dummyNodes.set(sortedIds, dummyNodeId);
        // Add the dummy node to the graph with minimal height
        dagreGraph.setNode(dummyNodeId, { width: 1, height: spouseDummyNodeHeight }); // Invisible node
        processedNodes.add(dummyNodeId);

        // Connect spouses to the dummy node in Dagre (invisible edges)
        dagreGraph.setEdge(sourceId, dummyNodeId, { weight: 5 }); // Higher weight to keep spouses close
        dagreGraph.setEdge(targetId, dummyNodeId, { weight: 5 });
    }
  });

  // 3. Process Parent/Child Relationships, connecting via Dummy Nodes if applicable
  parentChildEdges.forEach((edge) => {
    if (!edge || !edge.source || !edge.target || !edge.data?.rel_type) {
        console.warn("Skipping invalid parent/child edge in layout:", edge);
        return;
    }
      // Determine parent and child based on relationship type string
      const isParentRel = edge.data.rel_type.toLowerCase().includes('parent');
      const parentId = isParentRel ? edge.source : edge.target;
      const childId = isParentRel ? edge.target : edge.source;

      // Find if the parent is part of a spouse pair with a dummy node
      let parentUnitNodeId = parentId; // Default to parent node itself
      for (const [spousePairKey, dummyId] of dummyNodes.entries()) {
          if (spousePairKey.includes(parentId)) {
              parentUnitNodeId = dummyId; // Connect to/from the dummy node instead
              break;
          }
      }

      // Add edge to Dagre graph connecting child to the parent unit (parent node or dummy node)
      // Ensure direction is correct (Parent -> Child in TB layout)
      // Check if nodes exist in the graph before adding edge
      if (dagreGraph.hasNode(parentUnitNodeId) && dagreGraph.hasNode(childId)) {
           dagreGraph.setEdge(parentUnitNodeId, childId, { weight: 1 }); // Standard weight
      } else {
           console.warn(`Skipping edge in layout due to missing node: ${parentUnitNodeId} -> ${childId}`);
      }
  });

  // 4. Add Other Relationship Types (e.g., siblings) directly between people
  otherEdges.forEach((edge) => {
      if (!edge || !edge.source || !edge.target || !edge.data?.rel_type) {
          console.warn("Skipping invalid 'other' edge in layout:", edge);
          return;
      }
      // Avoid adding edges already implicitly handled via dummy nodes if necessary
      // For siblings, connect them directly
      if (edge.data.rel_type.toLowerCase().includes('sibling')) {
           // Check if nodes exist
           if (dagreGraph.hasNode(edge.source) && dagreGraph.hasNode(edge.target)) {
                dagreGraph.setEdge(edge.source, edge.target, { weight: 0.5 }); // Lower weight for siblings?
           } else {
                console.warn(`Skipping sibling edge in layout due to missing node: ${edge.source} -> ${edge.target}`);
           }
      }
      // Handle other types as needed
  });


  // 5. Run Dagre Layout
  dagre.layout(dagreGraph);

  // 6. Apply Positions to Original Nodes (excluding dummy nodes)
  const layoutedNodes = nodes.map((node) => {
    if (!node || !node.id) return node; // Skip invalid nodes

    const nodeWithPosition = dagreGraph.node(node.id);
    if (nodeWithPosition) { // Check if node exists in graph
        return {
            ...node,
            targetPosition: direction === 'LR' ? 'left' : 'top',
            sourcePosition: direction === 'LR' ? 'right' : 'bottom',
            // Center the node based on its dimensions
            position: {
                x: nodeWithPosition.x - nodeWidth / 2,
                y: nodeWithPosition.y - nodeHeight / 2,
            },
        };
    } else {
        console.warn(`Node ${node.id} not found in Dagre graph after layout.`);
        // Assign default position?
        return {
            ...node,
            position: { x: Math.random() * 400, y: Math.random() * 400 },
        };
    }
  });

  // Return original nodes with updated positions and original edges
  // React Flow doesn't need the dummy nodes or modified edges for rendering
  return { nodes: layoutedNodes, edges };
};


const FamilyTreeVisualization = ({ activeTreeId }) => { // Receive activeTreeId as prop
  const [selectedPersonData, setSelectedPersonData] = useState(null); // Store full data for details pane
  const [allNodesData, setAllNodesData] = useState([]); // Store all node data for lookups
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { fitView } = useReactFlow();
  const [isDarkMode, setIsDarkMode] = useState(
      window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  );
  const isInitialMount = useRef(true); // Ref to track initial mount

  // Listen for theme changes (optional)
  useEffect(() => {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e) => setIsDarkMode(e.matches);
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);


  // Fetch data using the single /tree_data endpoint
  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
        // Only fetch if activeTreeId is provided
        if (!activeTreeId) {
            if (isMounted) {
                setNodes([]);
                setEdges([]);
                setAllNodesData([]);
                setSelectedPersonData(null);
                setLoading(false);
                setError(null); // Clear error when no tree is selected
            }
            return;
        }

        setLoading(true);
        setError(null);
        try {
            // Use the getTreeData API call
            const treeData = await api.getTreeData(activeTreeId);

            if (isMounted) {
                // Validate response structure
                if (!treeData || !Array.isArray(treeData.nodes) || !Array.isArray(treeData.links)) {
                    throw new Error("Invalid data structure received from API.");
                }

                // Process nodes (already formatted by backend, just use them)
                const initialNodes = treeData.nodes.map(node => ({
                    ...node, // Use node structure from backend
                    // Ensure position is initialized if backend doesn't provide it
                    position: node.position || { x: 0, y: 0 },
                }));

                // Process edges (links from backend)
                const initialEdges = treeData.links.map(link => ({
                    ...link, // Use link structure from backend
                    id: link.id || `e-${link.source}-${link.target}-${link.label || 'rel'}`, // Ensure unique ID
                    type: link.type || 'default', // Default edge type
                    style: getEdgeStyle(link.label || link.data?.rel_type), // Apply styles
                    // Ensure data.rel_type exists for layout function
                    data: {
                        ...link.data,
                        rel_type: link.label || link.data?.rel_type,
                    }
                }));

                // Store all node data for PersonDetails lookup
                setAllNodesData(initialNodes.map(n => n.data)); // Store the 'data' part

                // Calculate layout if nodes exist
                if (initialNodes.length > 0) {
                    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                        initialNodes, initialEdges, rankdir
                    );
                    setNodes(layoutedNodes);
                    setEdges(initialEdges); // Use original edges for rendering

                    // Fit view only on initial load or when treeId changes significantly
                    if (isInitialMount.current) {
                         setTimeout(() => fitView({ padding: 0.2, duration: 800 }), 100);
                         isInitialMount.current = false;
                    }

                } else {
                    setNodes([]);
                    setEdges([]);
                    setAllNodesData([]);
                }
                setSelectedPersonData(null); // Clear selection when tree changes
            }
        } catch (err) {
            console.error("Error fetching tree data:", err);
            if (isMounted) {
                setError(err.response?.data?.message || err.message || "Failed to load family tree data.");
                setNodes([]);
                setEdges([]);
                setAllNodesData([]);
                setSelectedPersonData(null);
            }
        } finally {
            if (isMounted) setLoading(false);
        }
    };

    fetchData();

    // Reset initial mount flag when activeTreeId changes
    const initialMountTimer = setTimeout(() => {
        isInitialMount.current = true;
    }, 0);


    return () => {
        isMounted = false;
        clearTimeout(initialMountTimer);
    };
    // Dependency: Fetch data when activeTreeId changes
  }, [activeTreeId, setNodes, setEdges, fitView]);

  // Edge styling function
  const getEdgeStyle = (relationshipType) => {
    const typeLower = relationshipType?.toLowerCase();
    switch (typeLower) {
      // Use CSS variables for colors
      case 'spouse_current': case 'spouse_former': case 'partner':
        return { stroke: 'var(--color-relationship-spouse)', strokeWidth: 2 };
      case 'biological_parent': case 'adoptive_parent': case 'step_parent': case 'foster_parent': case 'guardian':
      case 'biological_child': case 'adoptive_child': case 'step_child': case 'foster_child':
        return { stroke: 'var(--color-relationship-parentchild)', strokeWidth: 2 };
      case 'sibling_full': case 'sibling_half': case 'sibling_step': case 'sibling_adoptive':
        return { stroke: 'var(--color-relationship-sibling)', strokeWidth: 1.5, strokeDasharray: '5,5' };
      default: return { stroke: 'var(--color-border)', strokeWidth: 1 }; // Default grey
    }
  };

  // Node click handler
  const onNodeClick = useCallback((event, node) => {
    // Find the full person data from the stored allNodesData array using the node id
    // The node object passed here is the React Flow node, use its id
    const personData = allNodesData.find(p => p.id === node.id);
    setSelectedPersonData(personData || node.data); // Pass the full person data object
    console.log("Selected Person Data:", personData || node.data);
  }, [allNodesData]); // Dependency on allNodesData array

  // Loading and error display
  if (loading) return <div className="card" style={{ padding: '20px', textAlign: 'center' }}>Loading family tree...</div>;
  // Show message if no tree is selected AFTER checking loading state
  if (!activeTreeId && !loading) return <div className="card" style={{ padding: '20px', textAlign: 'center' }}>Please select or create a family tree.</div>;
  if (error) return <div className="card message error-message" style={{ padding: '20px', textAlign: 'center' }}>Error: {error}</div>;
  if (nodes.length === 0 && !loading && !error && activeTreeId) return <div className="card" style={{ padding: '20px', textAlign: 'center' }}>No people found in this family tree. Add someone to get started!</div>;


  // React Flow specific theme adjustments (optional, CSS variables might suffice)
  const flowBgColor = isDarkMode ? 'var(--color-reactflow-bg)' : 'var(--color-reactflow-bg)';
  const minimapMaskColor = isDarkMode ? 'var(--color-reactflow-minimap-mask)' : 'var(--color-reactflow-minimap-mask)';

  return (
    // Use dashboard-main class for flex layout defined in index.css
    // This component itself doesn't need dashboard-main, it sits within dashboard-viz-container
    <>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes} // Register custom node types
          onNodeClick={onNodeClick}
          fitView // Fit view on initial load (handled by effect now)
          fitViewOptions={{ padding: 0.2 }} // Add padding around the graph
          proOptions={{ hideAttribution: true }} // Hide React Flow attribution
          minZoom={0.1} // Set min/max zoom levels
          maxZoom={2}
          style={{ background: flowBgColor }} // Apply background color via style prop
        >
          <MiniMap
              // nodeColor handled by node style or CSS
              // nodeStrokeColor handled by node style or CSS
              maskColor={minimapMaskColor} // Use state or CSS var
              pannable
              zoomable
          />
          <Controls />
          <Background
              // Use CSS var for background pattern color
              color={isDarkMode ? 'var(--color-border)' : '#ddd'}
              gap={16}
          />
        </ReactFlow>

        {/* Person Details Sidebar - Rendered by DashboardPage */}
        {/* We manage the selectedPersonData state here and pass it up or render details directly */}
        {/* For now, assume DashboardPage renders the sidebar and passes selectedPersonData */}
        {/* If this component should render the sidebar itself, move the sidebar div here */}
         <div className="dashboard-details-sidebar card">
             {/* Pass the selected person's data and the full list of node data */}
             <PersonDetails selectedPerson={selectedPersonData} allNodesData={allNodesData} activeTreeId={activeTreeId} />
         </div>
    </>
  );
};

// Wrap with ReactFlowProvider in the parent component (DashboardPage)
export default FamilyTreeVisualization;
