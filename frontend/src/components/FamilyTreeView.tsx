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
  zoom: number; // Made zoom non-optional, will default to 1
  offsetX?: number;
  offsetY?: number;
}

export interface ZoomControlFunctions {
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
  // Optional: pass current zoom level if buttons need to be disabled/styled based on it
  // getCurrentZoom?: () => number;
}

export interface LayoutControlFunctions {
  save: () => Promise<void>; // Assuming saveLayout is async
  reset: () => Promise<void>; // resetLayout will be async due to fetch
}

interface FamilyTreeViewProps {
  treeId: string;
  userId: string; // Assuming this comes from auth context or props
  onZoomControlsAvailable: (controls: ZoomControlFunctions) => void;
  onLayoutControlsAvailable: (controls: LayoutControlFunctions) => void; // New prop
}

const FamilyTreeView: React.FC<FamilyTreeViewProps> = ({ treeId, userId, onZoomControlsAvailable, onLayoutControlsAvailable }) => {
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1); // Default zoom level
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch layout from backend
  useEffect(() => {
    // Make zoom controls available to parent component
    onZoomControlsAvailable({
      zoomIn: () => setZoomLevel(prev => Math.min(prev * 1.2, 3)), // Max zoom 3x
      zoomOut: () => setZoomLevel(prev => Math.max(prev / 1.2, 0.5)), // Min zoom 0.5x
      resetZoom: () => setZoomLevel(1),
    });
  }, [onZoomControlsAvailable]); // Ensure this effect runs if the callback prop changes

  // Function to fetch layout, used by initial load and reset
  const fetchAndSetLayout = useCallback(async (isInitialLoad = false) => {
    if (!treeId || !userId) {
      if(isInitialLoad) setIsLoading(false);
      setError("Tree ID or User ID is missing for fetching layout.");
      return;
    }
    if(isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/tree_layouts/${treeId}/${userId}`);
      if (response.ok) {
        const data = await response.json();
        const fetchedLayoutData = data.layout_data as Partial<LayoutData>;
        const currentLayout: LayoutData = {
          positions: fetchedLayoutData.positions || [],
          zoom: fetchedLayoutData.zoom || 1,
          offsetX: fetchedLayoutData.offsetX,
          offsetY: fetchedLayoutData.offsetY,
        };
        setLayout(currentLayout);
        setZoomLevel(currentLayout.zoom);
        console.log("Layout fetched and applied:", currentLayout);
      } else if (response.status === 404) {
        const defaultLayout: LayoutData = { positions: [], zoom: 1 };
        setLayout(defaultLayout);
        setZoomLevel(defaultLayout.zoom);
        console.log(`No layout found for tree ${treeId} and user ${userId}. Initializing with default.`);
      } else {
        const errorData = await response.json();
        setError(errorData.error || `Failed to fetch layout: ${response.statusText}`);
      }
    } catch (err) {
      console.error("Fetch layout error:", err);
      setError(err instanceof Error ? err.message : "An unknown error occurred while fetching layout.");
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [treeId, userId]);


  // Initial layout fetch
  useEffect(() => {
    fetchAndSetLayout(true);
  }, [fetchAndSetLayout]);


  // Save layout to backend
  const saveLayout = useCallback(async (layoutToSave?: LayoutData) => {
    const currentLayoutToSave = layoutToSave || layout;
    if (!currentLayoutToSave) {
      console.error("No layout data to save.");
      setError("No layout data available to save.");
      return;
    }
    if (!treeId || !userId) {
      console.error("Cannot save layout: Tree ID or User ID is missing.");
      setError("Tree ID or User ID is missing for saving layout.");
      return;
    }

    console.log("Attempting to save layout:", currentLayoutToSave);
    try {
      const response = await fetch('/api/tree_layouts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          tree_id: treeId,
          layout_data: currentLayoutToSave,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        setError(errorData.error || `Failed to save layout: ${response.statusText}`);
        console.error("Failed to save layout:", errorData);
      } else {
        const result = await response.json();
        console.log("Layout saved successfully:", result);
        setError(null); // Clear previous errors
        // Optionally, show a success message to the user briefly
      }
    } catch (err) {
      console.error("Save layout error:", err);
      setError(err instanceof Error ? err.message : "An unknown error occurred while saving layout.");
    }
  }, [treeId, userId, layout]); // Added layout to dependencies of saveLayout

  const resetLayout = useCallback(async () => {
    console.log("Resetting layout...");
    await fetchAndSetLayout(false); // Fetch and apply, not as initial load
    // Potentially show a confirmation or status message
  }, [fetchAndSetLayout]);

  // Expose layout controls to parent
  useEffect(() => {
    onLayoutControlsAvailable({
      save: () => saveLayout(), // saveLayout can be called without args to save current state
      reset: resetLayout,
    });
  }, [onLayoutControlsAvailable, saveLayout, resetLayout]);

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

    // Preserve existing zoom level when only positions change
    const newLayout: LayoutData = { ...layout, positions: updatedPositions, zoom: zoomLevel };
    setLayout(newLayout); // Update local state immediately for responsiveness
    saveLayout(newLayout); // Debounce or throttle this in a real app
  };

  // Effect to update layout's zoom when zoomLevel state changes and then save
  useEffect(() => {
    if (layout && layout.zoom !== zoomLevel) {
      const newLayoutWithZoom: LayoutData = { ...layout, zoom: zoomLevel };
      setLayout(newLayoutWithZoom);
      // Auto-save when zoom changes, pass the specific layout to save
      saveLayout(newLayoutWithZoom);
      console.log(`Zoom changed to ${zoomLevel}, layout updated and auto-saved.`);
    }
    // Intentionally not including `layout` in dependency array if we only want this to trigger from `zoomLevel` changes.
    // However, if `layout` could change from elsewhere and `zoomLevel` is stale, this might need `layout` too.
    // Given current structure, `layout` state is updated first, then `saveLayout` is called.
    // Re-evaluating: `saveLayout` itself depends on `layout` state.
    // This effect is for auto-saving zoom changes.
  }, [zoomLevel, saveLayout]); // `layout` was removed from deps here to avoid loop if saveLayout updates layout. `saveLayout` has `layout` in its own deps.


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
