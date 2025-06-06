import React, { useState, useEffect, useCallback, FC, useRef, useMemo } from 'react'; // Added useMemo
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  DefaultEdgeOptions,
  FitViewOptions,
  MarkerType,
  NodeMouseHandler,
  EdgeMouseHandler,
  ReactFlowInstance,
  Viewport,
  NodeChange,
  OnMoveEnd,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  NodeTypes, // Added NodeTypes
} from 'reactflow';
import 'reactflow/dist/style.css';

import { getTreeData, Person, Relationship, TreeLayout, getTreeLayout, saveTreeLayout, NodePosition, addRelationship } from '../services/apiService';
import CustomPersonNode, { PersonNodeData } from './CustomPersonNode'; // Import custom node

interface FamilyTreeCanvasProps {
  treeId: string;
  userId?: string;
  onNodeSelect?: (node: Node | null) => void;
  onNodeDoubleClick?: (node: Node) => void;
  onEdgeSelect?: (edge: Edge | null) => void;
}

const fitViewOptions: FitViewOptions = {
  padding: 0.3,
};

const defaultEdgeOptions: DefaultEdgeOptions = {
  animated: false, // Turn off animation for potentially better performance with many edges
  type: 'smoothstep', // Default edge type
  markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15, color: '#a0a0a0' }, // Subtle arrow
  style: { strokeWidth: 1.5, stroke: '#a0a0a0' }, // Subtle edge color
};

// Define nodeTypes for React Flow
const nodeTypes: NodeTypes = {
  person: CustomPersonNode, // Map 'person' type to CustomPersonNode
};

// Helper to transform Person data to Node data, now using 'person' type
const personToNode = (person: Person, position?: NodePosition): Node<PersonNodeData> => {
  return {
    id: person.id,
    type: 'person', // Use the custom node type
    data: { // Structure this according to PersonNodeData
      name: person.name,
      birthDate: person.birthDate,
      deathDate: person.deathDate,
      photoUrl: person.photoUrl,
    },
    position: position ? { x: position.x, y: position.y } : { x: Math.random() * 400, y: Math.random() * 400 },
  };
};

const relationshipToEdge = (relationship: Relationship): Edge => ({
  id: relationship.id,
  source: relationship.person1Id,
  target: relationship.person2Id,
  label: relationship.type, // You might want to style this label or make it interactive
});

const FamilyTreeCanvas: FC<FamilyTreeCanvasProps> = ({
  treeId,
  userId,
  onNodeSelect,
  onNodeDoubleClick,
  onEdgeSelect,
}) => {
  const [nodes, setNodes] = useState<Node<PersonNodeData>[]>([]); // Specify Node data type
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const layoutChangedRef = useRef(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!treeId || !reactFlowInstance) { // Ensure reactFlowInstance is available
        if (!reactFlowInstance) console.log("[FamilyTreeCanvas] Waiting for ReactFlow instance...");
        if (!treeId) setError("No Tree ID provided.");
        setIsLoading(false); // Stop loading if essential params missing
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const [{ persons, relationships }, layout] = await Promise.all([
          getTreeData(treeId),
          getTreeLayout(treeId, userId)
        ]);

        const layoutPositionMap = new Map(layout?.positions?.map(p => [p.id, p]));
        const transformedNodes = persons.map(p => personToNode(p, layoutPositionMap.get(p.id)));
        const transformedEdges = relationships.map(relationshipToEdge);

        setNodes(transformedNodes);
        setEdges(transformedEdges);

        if (layout) {
          const viewport: Viewport = {
            x: layout.offsetX ?? 0,
            y: layout.offsetY ?? 0,
            zoom: layout.zoom ?? 1
          };
          reactFlowInstance.setViewport(viewport);
        }
        layoutChangedRef.current = false;
      } catch (err) {
        console.error('[FamilyTreeCanvas] Error fetching initial data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load tree data.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [treeId, userId, reactFlowInstance]);

  const onNodesChange: OnNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
    if (changes.some(change => change.type === 'position' && change.dragging === false)) {
      layoutChangedRef.current = true;
    }
  }, [setNodes]);

  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  const handleConnect: OnConnect = useCallback(async (connection) => {
    if (!connection.source || !connection.target) return;
    const newRelData = { person1Id: connection.source, person2Id: connection.target, type: 'related' as 'parent-child' }; // Temp type
    try {
      const newRelationship = await addRelationship(treeId, newRelData);
      setEdges((eds) => addEdge({ ...connection, id: newRelationship.id, label: newRelationship.type, type: 'smoothstep' }, eds));
      layoutChangedRef.current = true;
    } catch (apiError) {
      console.error("Failed to save new relationship via API", apiError);
    }
  }, [treeId, setEdges]);

  const handleNodeClick: NodeMouseHandler = useCallback((_event, node) => onNodeSelect?.(node), [onNodeSelect]);
  const handleNodeDoubleClick: NodeMouseHandler = useCallback((_event, node) => onNodeDoubleClick?.(node), [onNodeDoubleClick]);
  const handlePaneClick = useCallback(() => { onNodeSelect?.(null); onEdgeSelect?.(null); }, [onNodeSelect, onEdgeSelect]);
  const handleEdgeClick: EdgeMouseHandler = useCallback((_event, edge) => onEdgeSelect?.(edge), [onEdgeSelect]);

  const handleLayoutSave = useCallback(async () => {
    if (!reactFlowInstance || !treeId) return;
    const currentFlowState = reactFlowInstance.toObject();
    const layoutToSave: TreeLayout = {
      treeId, userId,
      positions: currentFlowState.nodes.map(n => ({ id: n.id, x: n.position.x, y: n.position.y })),
      zoom: currentFlowState.viewport.zoom,
      offsetX: currentFlowState.viewport.x,
      offsetY: currentFlowState.viewport.y,
    };
    try {
      await saveTreeLayout(layoutToSave);
      layoutChangedRef.current = false;
      console.log('[FamilyTreeCanvas] Layout saved.');
    } catch (err) { console.error('[FamilyTreeCanvas] Failed to save layout:', err); }
  }, [reactFlowInstance, treeId, userId]);

  const onMoveEnd: OnMoveEnd = useCallback(() => {
      if (!isLoading) { // Avoid marking as changed during initial load/fitView
        layoutChangedRef.current = true;
      }
  }, [isLoading]);

  const memoizedNodeTypes = useMemo(() => nodeTypes, []);

  if (isLoading && nodes.length === 0) return <div>Loading family tree...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ height: '100%', width: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={memoizedNodeTypes} // Pass custom node types
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        onInit={setReactFlowInstance}
        onMoveEnd={onMoveEnd}
        fitView={nodes.length > 0 && !layoutChangedRef.current && !isLoading}
        fitViewOptions={fitViewOptions}
        defaultEdgeOptions={defaultEdgeOptions}
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <MiniMap nodeStrokeWidth={3} zoomable pannable />
        <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 100 }}>
          <button onClick={handleLayoutSave} disabled={!layoutChangedRef.current && !isLoading}>
            Save Layout {layoutChangedRef.current ? '*' : ''}
          </button>
          {isLoading && <span style={{marginLeft: '10px'}}>Loading...</span>}
        </div>
      </ReactFlow>
    </div>
  );
};

export default FamilyTreeCanvas;
