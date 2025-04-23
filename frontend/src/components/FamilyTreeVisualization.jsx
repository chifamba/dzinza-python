import React, { useState, useEffect, useCallback } from 'react';
import dagre from 'dagre';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import PersonDetails from './PersonDetails';
import PersonNode from './PersonNode'; // Ensure PersonNode uses CSS vars/classes
import api from '../api';

// Define node types used in the flow
const nodeTypes = {
  personNode: PersonNode,
};

// Layout direction (Top to Bottom)
const rankdir = 'TB';
const nodeWidth = 172;
const nodeHeight = 80;

// Initialize Dagre graph
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

// Function to calculate layout using Dagre
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  dagreGraph.setGraph({ rankdir: direction });
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { label: node.data.label, width: nodeWidth, height: nodeHeight });
  });
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });
  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = direction === 'LR' ? 'left' : 'top';
    node.sourcePosition = direction === 'LR' ? 'right' : 'bottom';
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
  });
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
  // State to track current theme (optional, for dynamic prop changes)
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
    if (loading || error) return;

    const newNodes = people
        .filter(person => person && person.person_id)
        .map((person) => ({
            id: person.person_id.toString(),
            type: 'personNode',
            position: { x: 0, y: 0 },
            data: {
                id: person.person_id,
                label: `${person.first_name || ''} ${person.last_name || ''}`.trim(),
                dob: person.birth_date,
                dod: person.death_date,
            },
        }));

    const newEdges = relationships
      .filter(rel => rel && rel.rel_id && rel.person1_id && rel.person2_id)
      .map((relationship) => ({
        id: relationship.rel_id.toString(),
        source: relationship.person1_id.toString(),
        target: relationship.person2_id.toString(),
        type: 'default',
        animated: false,
        label: relationship.rel_type,
        style: getEdgeStyle(relationship.rel_type),
        data: relationship.attributes || {}
      }));

    if (newNodes.length > 0) {
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            newNodes, newEdges, rankdir
        );
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
        setTimeout(() => fitView({ padding: 0.1, duration: 800 }), 100);
    } else {
        setNodes([]);
        setEdges([]);
    }
  }, [people, relationships, loading, error, fitView, setNodes, setEdges]); // Added setNodes/setEdges

  // Edge styling (remains the same, colors defined elsewhere if needed)
  const getEdgeStyle = (relationshipType) => {
    const typeLower = relationshipType?.toLowerCase();
    switch (typeLower) {
      case 'spouse': case 'partner': return { stroke: '#e63946', strokeWidth: 2 };
      case 'parent': case 'child': return { stroke: '#457b9d', strokeWidth: 2 };
      case 'sibling': return { stroke: '#2a9d8f', strokeWidth: 2 };
      default: return { stroke: '#adb5bd', strokeWidth: 1 };
    }
  };

  // Node click handler
  const onNodeClick = useCallback((event, node) => {
    const personData = people.find(p => p.person_id === node.id);
    setSelectedPerson(personData || node.data);
  }, [people]);

  // Display loading/error
  if (loading) return <div style={{ padding: '20px', textAlign: 'center' }}>Loading family tree...</div>;
  if (error) return <div style={{ padding: '20px', textAlign: 'center', color: 'red' }}>Error: {error}</div>;

  // React Flow specific theme adjustments (optional, CSS variables might suffice)
  const flowBgColor = isDarkMode ? 'var(--color-reactflow-bg)' : 'var(--color-reactflow-bg)'; // Example using CSS var
  const minimapMaskColor = isDarkMode ? 'var(--color-reactflow-minimap-mask)' : 'var(--color-reactflow-minimap-mask)';
  // Node colors can be handled within PersonNode.jsx using CSS variables

  return (
    <div style={{ display: 'flex', height: '100%', gap: '10px' }}>
      {/* React Flow container */}
      <div style={{ flexGrow: 1, height: '100%', border: '1px solid var(--color-border)', borderRadius: '4px', backgroundColor: 'var(--color-reactflow-bg)' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          proOptions={{ hideAttribution: true }}
        >
          <MiniMap
              // nodeColor={node => node.type === 'personNode' ? 'var(--color-reactflow-node-bg)' : '#ddd'} // Example using CSS var
              // nodeStrokeColor={'var(--color-reactflow-node-border)'} // Example using CSS var
              maskColor={minimapMaskColor} // Use state or CSS var
              pannable
              zoomable
          />
          <Controls />
          <Background
              color={isDarkMode ? '#555' : '#ddd'} // Adjust background pattern color
              gap={16}
          />
        </ReactFlow>
      </div>
      {/* Person Details Sidebar */}
      <div className="card" style={{ width: '300px', flexShrink: 0, overflowY: 'auto' }}>
        {/* PersonDetails should use CSS variables/classes */}
        <PersonDetails selectedPerson={selectedPerson} people={people} />
      </div>
    </div>
  );
};

export default FamilyTreeVisualization;
