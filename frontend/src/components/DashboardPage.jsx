import React from 'react'; // Removed unused useState, useEffect
import { Link } from 'react-router-dom';
import FamilyTreeVisualization from './FamilyTreeVisualization';
import { ReactFlowProvider } from 'reactflow'; // Import ReactFlowProvider

function DashboardPage() {
  // Removed loading state as the visualization component handles its own data fetching

  // Basic styles (consider moving to CSS)
  const styles = {
      container: { padding: '20px' },
      buttonContainer: { marginBottom: '20px', display: 'flex', gap: '10px' },
      button: { padding: '8px 15px', cursor: 'pointer', borderRadius: '4px', border: '1px solid #ccc', backgroundColor: '#f0f0f0' },
      visualizationContainer: { height: '70vh', border: '1px solid #ddd', borderRadius: '4px' } // Ensure height is set
  };

  return (
    <div style={styles.container}>
      {/* Buttons to navigate to Add pages */}
      <div style={styles.buttonContainer}>
        <Link to="/add-person">
          <button style={styles.button}>Add Person</button>
        </Link>
        <Link to="/add-relationship">
          <button style={styles.button}>Add Relationship</button>
        </Link>
      </div>

      {/* Wrap Visualization in Provider */}
      <div style={styles.visualizationContainer}>
         <ReactFlowProvider>
             <FamilyTreeVisualization />
         </ReactFlowProvider>
      </div>
    </div>
  );
}

export default DashboardPage;
