import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import FamilyTreeVisualization from './FamilyTreeVisualization';

function DashboardPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate data fetching delay
    setTimeout(() => {
      setLoading(false);
    }, 500);
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <Link to="/add-person">
        

          <button>Add Person</button>
        </Link>
        <Link to="/add-relationship">
          <button>Add Relationship</button>
        </Link>
      </div>
        <FamilyTreeVisualization/>
        {loading && <div>Loading...</div>}
        {!loading && <FamilyTreeVisualization />}
    </div>


  );
}

export default DashboardPage;