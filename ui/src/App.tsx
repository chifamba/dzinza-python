import { ReactFlowProvider } from 'reactflow';
import type { Node, Edge } from 'reactflow'; // Use type import
import FamilyTreeCanvas from './components/FamilyTreeCanvas';
import './App.css';

function App() {
  const currentTreeId = "mockTree123";
  const currentUserId = "userTest1"; // Example User ID

  const handleNodeSelect = (node: Node | null) => {
    if (node) {
      console.log('[App] Node selected:', node);
      // Here you would typically display more info about the node
    } else {
      console.log('[App] Selection cleared (pane click)');
    }
  };

  const handleNodeDoubleClick = (node: Node) => {
    console.log('[App] Node double-clicked (for edit):', node);
    // Here you would typically open an edit modal/form
  };

  const handleEdgeSelect = (edge: Edge | null) => {
    if (edge) {
      console.log('[App] Edge selected:', edge);
    } else {
      console.log('[App] Edge selection cleared');
    }
  };

  return (
    <ReactFlowProvider>
      <div style={{ height: '100vh', width: '100vw' }}>
        <FamilyTreeCanvas
          treeId={currentTreeId}
          userId={currentUserId}
          onNodeSelect={handleNodeSelect}
          onNodeDoubleClick={handleNodeDoubleClick}
          onEdgeSelect={handleEdgeSelect}
        />
      </div>
    </ReactFlowProvider>
  );
}

export default App;
