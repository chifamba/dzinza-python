import React, { useState, useEffect, useCallback } from 'react';

// Placeholder for actual layout data structure
interface CardPosition {
  id: string; // Person ID
  x: number;
  y: number;
}

interface LayoutData {
  positions: CardPosition[];
  // Add other layout-specific properties here, e.g., zoom level, canvas offset
  zoom?: number;
  offsetX?: number;
  offsetY?: number;
}

interface FamilyTreeViewProps {
  treeId: string;
  userId: string; // Assuming this comes from auth context or props
  // onLayoutChange?: (layout: LayoutData) => void; // Callback for when layout is changed by user
}

const FamilyTreeView: React.FC<FamilyTreeViewProps> = ({ treeId, userId }) => {
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch layout from backend
  useEffect(() => {
    if (!treeId || !userId) {
      setIsLoading(false);
      setError("Tree ID or User ID is missing.");
      return;
    }

    const fetchLayout = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/tree_layouts/${treeId}/${userId}`);
        if (response.ok) {
          const data = await response.json();
          setLayout(data.layout_data); // Assuming API returns { ..., layout_data: { positions: [...] } }
        } else if (response.status === 404) {
          // Layout not found, use a default or empty layout
          setLayout({ positions: [] }); // Initialize with an empty layout
          console.log(`No layout found for tree ${treeId} and user ${userId}. Initializing with default.`);
        } else {
          const errorData = await response.json();
          setError(errorData.error || `Failed to fetch layout: ${response.statusText}`);
        }
      } catch (err) {
        console.error("Fetch layout error:", err);
        setError(err instanceof Error ? err.message : "An unknown error occurred while fetching layout.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchLayout();
  }, [treeId, userId]);

  // Save layout to backend
  const saveLayout = useCallback(async (newLayoutData: LayoutData) => {
    if (!treeId || !userId) {
      console.error("Cannot save layout: Tree ID or User ID is missing.");
      // Optionally, set an error state here to inform the user
      return;
    }

    try {
      const response = await fetch('/api/tree_layouts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          tree_id: treeId,
          layout_data: newLayoutData,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        // Set an error state to provide feedback to the user
        setError(errorData.error || `Failed to save layout: ${response.statusText}`);
        console.error("Failed to save layout:", errorData);
      } else {
        const result = await response.json();
        console.log("Layout saved successfully:", result);
        // Optionally, update local state if server returns the saved layout with new IDs/timestamps
        // For example, if the API returns the full layout object: setLayout(result.layout.layout_data);
        // Or simply clear any save-related error messages
        setError(null);
      }
    } catch (err) {
      console.error("Save layout error:", err);
      // Set an error state
      setError(err instanceof Error ? err.message : "An unknown error occurred while saving layout.");
    }
  }, [treeId, userId]);

  // Placeholder function to simulate a layout change
  const handleMoveCard = (personId: string, newX: number, newY: number) => {
    if (!layout) return;

    const updatedPositions = layout.positions.map(p =>
      p.id === personId ? { ...p, x: newX, y: newY } : p
    );

    // If the person wasn't in the layout, add them (basic example)
    if (!updatedPositions.find(p => p.id === personId)) {
        updatedPositions.push({ id: personId, x: newX, y: newY });
    }

    const newLayout: LayoutData = { ...layout, positions: updatedPositions };
    setLayout(newLayout); // Update local state immediately for responsiveness
    saveLayout(newLayout); // Debounce or throttle this in a real app
  };

  if (isLoading) {
    return <div>Loading layout...</div>;
  }

  if (error) {
    return <div>Error: {error} <button onClick={() => { /* allow refetch or clear error */ }}>Retry</button></div>;
  }

  return (
    <div>
      <h2>Family Tree View (Tree: {treeId}, User: {userId})</h2>
      {/* Placeholder for actual tree rendering using 'layout' state */}
      <p>Layout Data: {JSON.stringify(layout)}</p>

      {/* Example controls to simulate layout changes */}
      <button onClick={() => handleMoveCard('person1', Math.random() * 500, Math.random() * 300)}>
        Move Person 1
      </button>
      <button onClick={() => handleMoveCard('person2', Math.random() * 500, Math.random() * 300)}>
        Move Person 2
      </button>

      {/*
        In a real application, the tree visualization (e.g., using a library like React Flow, D3, or custom canvas rendering)
        would call handleMoveCard (or a similar function) when a user drags and drops a card.
        The actual rendering of nodes/cards based on layout.positions would go here.
      */}
    </div>
  );
};

export default FamilyTreeView;
