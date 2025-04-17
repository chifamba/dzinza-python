import React from 'react';\n+import ReactFlow, {
    Background,
    Controls,
    MiniMap,
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import PersonDetails from './PersonDetails';

const FamilyTreeVisualization = () => {
  const [selectedPerson, setSelectedPerson] = useState(null);

  return (
    <div style={{ width: '100%', height: '500px', display: 'flex' }}>
      <ReactFlow>
        <MiniMap />
        <Controls />
        <Background />
      </ReactFlow>
      <PersonDetails selectedPerson={selectedPerson} />
      </div>
  );
};

export default FamilyTreeVisualization;