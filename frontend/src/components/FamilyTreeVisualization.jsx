import React, { useState, useEffect } from 'react';
import dagre from 'dagre';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  getBezierPath
} from 'reactflow';
import 'reactflow/dist/style.css';
import PersonDetails from './PersonDetails';
import PersonNode from './PersonNode';
import api from '../api';

const nodeTypes = {
  personNode: PersonNode,
};

const FamilyTreeVisualization = () => {
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [people, setPeople] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { setViewport } = useReactFlow();
  const nodeWidth = 172;
  const nodeHeight = 36;

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const getLayoutedElements = (nodes, edges) => {
    dagreGraph.setGraph({ rankdir: 'TB' });
    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });
    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });
    dagre.layout(dagreGraph);
    return nodes.map((node) => ({ ...node, position: dagreGraph.node(node.id) }));
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const peopleData = await api.getAllPeople();
        const relationshipsData = await api.getAllRelationships();
        setPeople(peopleData);
        setRelationships(relationshipsData);
      } catch (error) {
        console.error("Error fetching data", error);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    const newNodes = people.map((person) => {
      return {
        id: person.id.toString(),
        type: 'personNode',
        position: { x: 0, y: 0 },
        data: { ...person, label: `${person.firstName} ${person.lastName}`, dateOfBirth: person.dateOfBirth },
        sourcePosition: 'bottom',
        targetPosition: 'top'
      };
    });

    const newEdges = relationships.map((relationship) => ({
      id: relationship.id.toString(),
      source: relationship.person1.toString(),
      target: relationship.person2.toString(),
      type: relationship.relationshipType, // Include relationship type
      animated: true,
      style: getEdgeStyle(relationship.relationshipType), // Apply conditional styling
    }));

    const layoutedNodes = getLayoutedElements(newNodes, newEdges);
    setNodes(layoutedNodes);
    setEdges(newEdges);
  }, [people, relationships]);
  
    // Helper function for conditional edge styling
  const getEdgeStyle = (relationshipType) => {
    switch (relationshipType) {
      case 'spouse':
        return { stroke: 'red', strokeWidth: 3 };
      case 'parent':
        return { stroke: 'blue', strokeWidth: 2 };
      case 'child':
        return { stroke: 'green', strokeWidth: 2 };
      case 'sibling':
        return { stroke: 'purple', strokeWidth: 2 };
      default:
        return { stroke: 'gray', strokeWidth: 1 };
    }
  };

  const onNodeClick = (event, node) => {
    setSelectedPerson(node.data);
    setViewport({ x: 0, y: 0, zoom: 1});
  };
  
  return (
    <div style={{ width: '100%', height: '500px', display: 'flex' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
      >
        <MiniMap />
        <Controls />
        <Background />
      </ReactFlow>
      <PersonDetails selectedPerson={selectedPerson} />
    </div>
  );
};

export default FamilyTreeVisualization;
