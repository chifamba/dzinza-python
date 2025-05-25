import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import FamilyTreeVisualization from './FamilyTreeVisualization';
import { ReactFlowProvider } from 'reactflow';
import { useAuth } from '../context/AuthContext';
import api from '../api';

function DashboardPage() {
  const { user, activeTreeId, selectActiveTree, loading: authLoading } = useAuth();
  const [userTrees, setUserTrees] = useState([]);
  const [loadingTrees, setLoadingTrees] = useState(true);
  const [treesError, setTreesError] = useState(null);
  const [creatingTree, setCreatingTree] = useState(false);
  const [newTreeName, setNewTreeName] = useState('');
  const [newTreeError, setNewTreeError] = useState(null);

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
  }, [user]);

  const handleTreeSelect = (event) => {
    const treeId = event.target.value;
    if (treeId) {
      selectActiveTree(treeId);
    }
  };

  const handleCreateTree = async () => {
    if (!newTreeName.trim()) {
      setNewTreeError("Tree name cannot be empty.");
      return;
    }
    setCreatingTree(true);
    setNewTreeError(null);
    try {
      const newTree = await api.createTree({ name: newTreeName });
      setUserTrees(prevTrees => [...prevTrees, newTree]);
      selectActiveTree(newTree.id);
      setNewTreeName('');
    } catch (err) {
      console.error("Failed to create tree:", err);
      const errorMsg = err.response?.data?.message || err.message || 'Failed to create tree.';
      setNewTreeError(errorMsg);
    } finally {
      setCreatingTree(false);
    }
  };

  if (authLoading || loadingTrees) {
    return <div className="main-content-area">Loading dashboard...</div>;
  }

  if (treesError) {
    return <div className="main-content-area message error-message">Error: {treesError}</div>;
  }

  return (
    <div className="main-content-area dashboard-layout">
      <div className="dashboard-controls card">
        <h2>Your Trees</h2>
        {userTrees.length > 0 ? (
          <div className="form-group" style={{ maxWidth: '300px' }}>
            <label htmlFor="tree-select">Select Active Tree:</label>
            <select 
              id="tree-select" 
              value={activeTreeId || ''} 
              onChange={handleTreeSelect}
              className="w-full p-2 border rounded"
            >
              <option value="" disabled>-- Select a Tree --</option>
              {userTrees.map(tree => (
                <option key={tree.id} value={tree.id}>{tree.name}</option>
              ))}
            </select>
          </div>
        ) : (
          <p>No trees found. Create one below!</p>
        )}

        <div className="mt-4">
          <label htmlFor="new-tree-name">New Tree Name:</label>
          <div className="flex gap-2">
            <input
              type="text"
              id="new-tree-name"
              value={newTreeName}
              onChange={(e) => setNewTreeName(e.target.value)}
              disabled={creatingTree}
              className="flex-1 p-2 border rounded"
            />
            <button 
              onClick={handleCreateTree} 
              disabled={creatingTree}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              {creatingTree ? 'Creating...' : 'Create New Tree'}
            </button>
          </div>
          {newTreeError && <div className="text-red-500 mt-2">{newTreeError}</div>}
        </div>

        <div className="button-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '1rem' }}>
          <Link to="/add-person" className="button">Add Person</Link>
          <Link to="/add-existing-person" className="button">Add Existing Person</Link>
          <Link to="/add-relationship" className="button">Add Relationship</Link>
        </div>
      </div>

      <div className="visualization-container card" style={{ flexGrow: 1, minHeight: '500px', position: 'relative' }}>
        {activeTreeId ? (
          <ReactFlowProvider>
            <FamilyTreeVisualization activeTreeId={activeTreeId} />
          </ReactFlowProvider>
        ) : (
          <div className="dashboard-viz-container card">
            <p>Please select or create a family tree to view the visualization.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;