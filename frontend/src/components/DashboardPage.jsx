import React, { useState, useEffect } from 'react'; // Added useState, useEffect
import { Link } from 'react-router-dom';
import FamilyTreeVisualization from './FamilyTreeVisualization';
import { ReactFlowProvider } from 'reactflow';
import { useAuth } from '../context/AuthContext'; // Import useAuth
import api from '../api'; // Import api

function DashboardPage() {
  const { user, activeTreeId, selectActiveTree, loading: authLoading } = useAuth(); // Get auth state and functions
  const [userTrees, setUserTrees] = useState([]);
  const [loadingTrees, setLoadingTrees] = useState(true);
  const [treesError, setTreesError] = useState(null);
  const [creatingTree, setCreatingTree] = useState(false);
  const [newTreeName, setNewTreeName] = useState('');
  const [newTreeError, setNewTreeError] = useState(null);


  // Fetch user's trees on component mount or when user changes
  useEffect(() => {
    let isMounted = true;
    const fetchUserTrees = async () => {
        if (!user) {
            setUserTrees([]);
            setLoadingTrees(false);
            return;
        }
        setLoadingTrees(true);
        setTreesError(null);
        try {
            const treesData = await api.getUserTrees();
            if (isMounted) {
                 setUserTrees(Array.isArray(treesData) ? treesData : []);
                 // If user has trees but no active tree is set, maybe set the first one?
                 // This depends on desired UX. For now, we rely on session or user selection.
            }
        } catch (err) {
            console.error("Failed to fetch user trees:", err);
            if (isMounted) {
                 setTreesError("Failed to load your family trees.");
                 setUserTrees([]);
            }
        } finally {
            if (isMounted) setLoadingTrees(false);
        }
    };

    fetchUserTrees();
    return () => { isMounted = false; };
  }, [user]); // Dependency on user to re-fetch if login state changes

  // Handle tree selection from dropdown
  const handleTreeSelect = (event) => {
    const treeId = event.target.value;
    if (treeId) {
      selectActiveTree(treeId); // Use the selectActiveTree function from context
    }
  };

   // Handle new tree creation
   const handleCreateTree = async () => {
       if (!newTreeName.trim()) {
           setNewTreeError("Tree name cannot be empty.");
           return;
       }
       setCreatingTree(true);
       setNewTreeError(null);
       try {
           const newTree = await api.createTree({ name: newTreeName });
           // Add the new tree to the list and set it as active
           setUserTrees(prevTrees => [...prevTrees, newTree]);
           selectActiveTree(newTree.id); // Set the newly created tree as active
           setNewTreeName(''); // Clear input
       } catch (err) {
           console.error("Failed to create tree:", err);
            const errorMsg = err.response?.data?.message || err.message || 'Failed to create tree.';
           setNewTreeError(errorMsg);
       } finally {
           setCreatingTree(false);
       }
   };

  // Basic styles (consider moving to CSS) - Updated to use CSS classes
  // Removed inline styles where classes are appropriate
   if (authLoading || loadingTrees) {
       return <div className="main-content-area">Loading dashboard...</div>;
   }

   if (treesError) {
       return <div className="main-content-area message error-message">Error: {treesError}</div>;
   }


  return (
    // Use main-content-area class for padding/max-width, dashboard-layout for internal flex
    <div className="main-content-area dashboard-layout">
      {/* Tree Selection and Creation Controls */}
      <div className="dashboard-controls card"> {/* Use card class for styling */}
          <h2>Your Trees</h2>
          {userTrees.length > 0 ? (
              <div className="form-group" style={{ maxWidth: '300px' }}> {/* Limit width for dropdown */}
                  <label htmlFor="tree-select">Select Active Tree:</label>
                  <select id="tree-select" value={activeTreeId || ''} onChange={handleTreeSelect}>
                      <option value="" disabled>-- Select a Tree --</option>
                      {userTrees.map(tree => (
                          <option key={tree.id} value={tree.id}>{tree.name}</option>
                      ))}
                  </select>
              </div>
          ) : (
              <p>No trees found. Create one below!</p>
          )}

           {/* New Tree Creation Form */}
           <div style={{ marginTop: '1rem' }}>
               <label htmlFor="new-tree-name">New Tree Name:</label>
               <input
                   type="text"
                   id="new-tree-name"
                   value={newTreeName}
                   onChange={(e) => setNewTreeName(e.target.value)}
                   disabled={creatingTree}
                   style={{ display: 'inline-block', width: 'auto', marginRight: '10px' }} // Adjust input style
               />
               <button onClick={handleCreateTree} disabled={creatingTree}>
                   {creatingTree ? 'Creating...' : 'Create New Tree'}
               </button>
               {newTreeError && <div className="field-error" style={{ marginTop: '5px' }}>{newTreeError}</div>}
           </div>

          {/* Buttons to navigate to Add pages - Use dashboard-controls class for flex */}
          <div className="dashboard-controls" style={{ marginTop: '1.5rem', borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
            <Link to="/add-person" className="button">Add Person</Link> {/* Use button class */}
            <Link to="/add-relationship" className="button">Add Relationship</Link> {/* Use button class */}
          </div>
      </div>


      {/* Family Tree Visualization */}
      {activeTreeId ? (
          // Wrap Visualization in ReactFlowProvider and dashboard-viz-container
          <div className="dashboard-viz-container">
             <ReactFlowProvider>
                 {/* Pass activeTreeId to the visualization component */}
                 <FamilyTreeVisualization activeTreeId={activeTreeId} />
             </ReactFlowProvider>
          </div>
      ) : (
          <div className="dashboard-viz-container card"> {/* Use card class */}
               <p>Please select or create a family tree to view the visualization.</p>
          </div>
      )}
       {/* Person Details Sidebar - Render always, content is conditional */}
       {/* Sidebar content is handled within PersonDetails */}
    </div>
  );
}

export default DashboardPage;
