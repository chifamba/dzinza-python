import React, { useState, useEffect, useCallback } from 'react';
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
  const dagreGraph = new dagre.graphlib.Graph({ compound: true }); // Use compound graph for potential grouping
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
      rankdir: direction,
      ranksep: 60, // Increase separation between ranks (generations)
      nodesep: 30, // Increase separation between nodes in the same rank
      align: 'UL', // Align nodes to upper-left in their rank cell
  });

  const spouseEdges = edges.filter(edge => edge.data?.rel_type?.toLowerCase() === 'spouse' || edge.data?.rel_type?.toLowerCase() === 'partner');
  const parentChildEdges = edges.filter(edge => edge.data?.rel_type?.toLowerCase() === 'parent' || edge.data?.rel_type?.toLowerCase() === 'child');
  const otherEdges = edges.filter(edge => !spouseEdges.includes(edge) && !parentChildEdges.includes(edge));

  const processedNodes = new Set(); // Keep track of nodes already added
  const dummyNodes = new Map(); // Store dummy nodes: key = sorted spouse IDs string, value = dummy node ID

  // 1. Add Person Nodes to Dagre Graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { label: node.data.label, width: nodeWidth, height: nodeHeight });
    processedNodes.add(node.id);
  });

  // 2. Process Spouse Relationships and Create Dummy Nodes
  spouseEdges.forEach((edge) => {
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
        // These edges help dagre place the dummy node between spouses
        dagreGraph.setEdge(sourceId, dummyNodeId, { weight: 5 }); // Higher weight to keep spouses close
        dagreGraph.setEdge(targetId, dummyNodeId, { weight: 5 });
    }
  });

  // 3. Process Parent/Child Relationships, connecting via Dummy Nodes if applicable
  parentChildEdges.forEach((edge) => {
      const parentId = edge.data?.rel_type?.toLowerCase() === 'parent' ? edge.source : edge.target;
      const childId = edge.data?.rel_type?.toLowerCase() === 'parent' ? edge.target : edge.source;

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
      dagreGraph.setEdge(parentUnitNodeId, childId, { weight: 1 }); // Standard weight
  });

  // 4. Add Other Relationship Types (e.g., siblings) directly between people
  otherEdges.forEach((edge) => {
      // Avoid adding edges already implicitly handled via dummy nodes if necessary
      // For siblings, connect them directly
      if (edge.data?.rel_type?.toLowerCase() === 'sibling') {
           dagreGraph.setEdge(edge.source, edge.target, { weight: 0.5 }); // Lower weight for siblings?
      }
      // Handle other types as needed
  });


  // 5. Run Dagre Layout
  dagre.layout(dagreGraph);

  // 6. Apply Positions to Original Nodes (excluding dummy nodes)
  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    if (nodeWithPosition) { // Check if node exists in graph (it should)
        node.targetPosition = direction === 'LR' ? 'left' : 'top';
        node.sourcePosition = direction === 'LR' ? 'right' : 'bottom';
        // Center the node based on its dimensions
        node.position = {
            x: nodeWithPosition.x - nodeWidth / 2,
            y: nodeWithPosition.y - nodeHeight / 2,
        };
    } else {
        console.warn(`Node ${node.id} not found in Dagre graph after layout.`);
        // Assign default position?
        node.position = { x: Math.random() * 400, y: Math.random() * 400 };
    }
  });

  // Return original nodes with updated positions and original edges
  // React Flow doesn't need the dummy nodes or modified edges for rendering
  return { nodes, edges };
};


const FamilyTreeVisualization = () => {
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [people, setPeople] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { fitView } = useReactFlow();
  const [isDarkMode, setIsDarkMode] = useState(
      window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  );

  // Listen for theme changes (optional)
  useEffect(() => {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e) => setIsDarkMode(e.matches);
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);


  // Fetch data from API
  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [peopleData, relationshipsData] = await Promise.all([
          api.getAllPeople(),
          api.getAllRelationships()
        ]);
        if (isMounted) {
          setPeople(Array.isArray(peopleData) ? peopleData : []);
          setRelationships(Array.isArray(relationshipsData) ? relationshipsData : []);
        }
      } catch (err) {
        console.error("Error fetching data:", err);
        if (isMounted) {
            setError("Failed to load family tree data.");
            setPeople([]);
            setRelationships([]);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => { isMounted = false; };
  }, []);

  // Update nodes and edges when data changes
  useEffect(() => {
    if (loading || error || people.length === 0) return; // Wait for data

    // Create initial nodes from people data
    const initialNodes = people
        .filter(person => person && person.person_id)
        .map((person) => ({
            id: person.person_id.toString(),
            type: 'personNode', // Use custom node type
            position: { x: 0, y: 0 }, // Initial position, layout engine will override
            data: { // Data to pass to PersonNode component
                id: person.person_id,
                label: `${person.first_name || ''} ${person.last_name || ''}`.trim(),
                dob: person.birth_date,
                dod: person.death_date,
                // Add photoUrl or other needed data here
                // photoUrl: person.photo_url || defaultAvatar,
            },
        }));

    // Create initial edges from relationships data
    const initialEdges = relationships
      .filter(rel => rel && rel.rel_id && rel.person1_id && rel.person2_id)
      .map((relationship) => ({
        id: `e-${relationship.rel_id}`, // Ensure unique edge IDs, prefix with 'e-'
        source: relationship.person1_id.toString(),
        target: relationship.person2_id.toString(),
        type: 'default', // Use 'smoothstep' or 'step' for different edge shapes
        // markerEnd: { // Add arrow heads if desired
        //   type: MarkerType.ArrowClosed,
        // },
        animated: false, // Optional animation
        label: relationship.rel_type, // Display relationship type on edge
        style: getEdgeStyle(relationship.rel_type), // Apply styles based on type
        data: { // Pass relationship data if needed (e.g., for edge click handlers)
            ...relationship,
            rel_type: relationship.rel_type // Ensure rel_type is in data for layout function
        }
      }));

    // Calculate layout if nodes exist
    if (initialNodes.length > 0) {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            initialNodes, initialEdges, rankdir
        );
        setNodes(layoutedNodes);
        // Use the original edges for rendering, not the modified ones used by Dagre
        setEdges(initialEdges);
        // Fit view after a short delay to allow rendering
        setTimeout(() => fitView({ padding: 0.2, duration: 800 }), 100);
    } else {
        setNodes([]);
        setEdges([]);
    }
  // Dependencies for re-running layout: people, relationships, loading state, errors, and React Flow setters/methods
  }, [people, relationships, loading, error, fitView, setNodes, setEdges]);

  // Edge styling function (remains the same)
  const getEdgeStyle = (relationshipType) => {
    const typeLower = relationshipType?.toLowerCase();
    switch (typeLower) {
      case 'spouse': case 'partner': return { stroke: '#e63946', strokeWidth: 2 }; // Red for partners
      case 'parent': case 'child': return { stroke: '#457b9d', strokeWidth: 2 }; // Blue for parent/child
      case 'sibling': return { stroke: '#2a9d8f', strokeWidth: 1.5, strokeDasharray: '5,5' }; // Green dashed for siblings
      default: return { stroke: 'var(--color-border)', strokeWidth: 1 }; // Default grey
    }
  };

  // Node click handler (remains the same)
  const onNodeClick = useCallback((event, node) => {
    // Find the full person object from the people array using the node id
    const personData = people.find(p => p.person_id === node.id);
    setSelectedPerson(personData || node.data); // Pass the full person object
  }, [people]); // Dependency on people array

  // Loading and error display
  if (loading) return <div style={{ padding: '20px', textAlign: 'center' }}>Loading family tree...</div>;
  if (error) return <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-error-text)' }}>Error: {error}</div>;
  if (nodes.length === 0 && !loading) return <div style={{ padding: '20px', textAlign: 'center' }}>No people found in the family tree.</div>;

  // React Flow specific theme adjustments (optional, CSS variables might suffice)
  const flowBgColor = isDarkMode ? 'var(--color-reactflow-bg)' : 'var(--color-reactflow-bg)';
  const minimapMaskColor = isDarkMode ? 'var(--color-reactflow-minimap-mask)' : 'var(--color-reactflow-minimap-mask)';

  return (
    // Use dashboard-main class for flex layout defined in index.css
    <div className="dashboard-main" style={{ height: '100%' }}>
      {/* React Flow container */}
      {/* Use dashboard-viz-container class */}
      <div className="dashboard-viz-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes} // Register custom node types
          onNodeClick={onNodeClick}
          fitView // Fit view on initial load
          fitViewOptions={{ padding: 0.2 }} // Add padding around the graph
          proOptions={{ hideAttribution: true }} // Hide React Flow attribution
          minZoom={0.1} // Set min/max zoom levels
          maxZoom={2}
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
      </div>
      {/* Person Details Sidebar */}
      {/* Use dashboard-details-sidebar and card classes */}
      <div className="dashboard-details-sidebar card">
        <PersonDetails selectedPerson={selectedPerson} people={people} />
      </div>
    </div>
  );
};

// Wrap with ReactFlowProvider in the parent component (DashboardPage)
// export default FamilyTreeVisualization; // Export without provider here

// Correct: Export the component directly
export default FamilyTreeVisualization;
