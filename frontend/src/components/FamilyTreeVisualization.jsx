// frontend/src/components/FamilyTreeVisualization.jsx
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { ResponsiveNeoGraph } from 'neovis.js-react'; // Ensure this is the correct library if you installed a wrapper
import { getFamilyTree } from '../api'; // API function to fetch tree data from backend

// Neo4j Connection Details from environment variables
const NEO4J_URI = import.meta.env.VITE_NEO4J_URI;
const NEO4J_USER = import.meta.env.VITE_NEO4J_USER;
const NEO4J_PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD;

const FamilyTreeVisualization = ({ familyTreeId, onNodeSelected }) => {
  // State for graph data, loading status, and errors
  const [rawData, setRawData] = useState(null); // To store data from getFamilyTree if needed elsewhere
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // setError is defined here
  const [activeNodeDetails, setActiveNodeDetails] = useState(null); // Details of the clicked node

  // Ref to track if the component is mounted
  const isMounted = useRef(true);

  // Style for the NeoGraph container
  const containerStyle = {
    width: '100%',
    height: '100%',
    border: '1px solid #ddd', // Theme-consistent border
    borderRadius: '0.5rem', // Tailwind's rounded-lg equivalent
    overflow: 'hidden',
    backgroundColor: '#f9fafb', // A light background color
  };

  // Effect to set isMounted ref on mount and unmount
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false; // Set to false when component unmounts
    };
  }, []);

  // Callback to fetch and process tree data for the visualization
  // This function is called when familyTreeId changes.
  // Note: ResponsiveNeoGraph connects directly to Neo4j.
  // This function might be for fetching supplementary data or if an alternative visualization was planned.
  // For now, it will manage loading/error states around the expectation of the graph rendering.
  const loadTreeData = useCallback(async (treeId) => {
    if (!isMounted.current) {
      console.log("FamilyTreeVisualization.loadTreeData: component unmounted, aborting.");
      return;
    }
    console.log(`FamilyTreeVisualization.loadTreeData: called with treeId: ${treeId}`);
    setLoading(true);
    setError(null); // Clear previous errors, this is the key call

    try {
      // If you need to fetch data via backend API (e.g., for non-NeoGraph parts or pre-processing)
      // const treeData = await getFamilyTree(treeId);
      // if (!isMounted.current) return;
      // if (treeData) {
      //   setRawData(treeData);
      // } else {
      //   throw new Error('Fetched tree data is invalid or empty.');
      // }
      // For now, we assume ResponsiveNeoGraph handles its own data fetching via Cypher.
      // So, this function primarily manages loading/error states for the visual component.
      // If ResponsiveNeoGraph itself provides loading/error callbacks, those might be more direct.
      // Simulating a brief load period if NeoGraph doesn't expose its own.
      // In a real scenario, you'd tie this to NeoGraph's lifecycle if possible.
      // If getFamilyTree was essential, ensure it's called and its data used.
    } catch (err) {
      console.error("Error in loadTreeData:", err);
      if (isMounted.current) {
        setError(err.message || 'Failed to prepare tree data.');
        setRawData(null);
      }
    } finally {
      if (isMounted.current) {
        // setLoading(false); // Set to false after NeoGraph indicates it has rendered/failed
        // For now, we'll set it false after a short delay, assuming NeoGraph will take over.
        // This is a placeholder if NeoGraph doesn't have explicit loading state management accessible here.
        setTimeout(() => {
            if(isMounted.current) setLoading(false);
        }, 500); // Small delay
      }
    }
  }, [/* getFamilyTree if it were used and its reference could change */]); // Dependencies for useCallback

  // Effect to load data when familyTreeId changes
  useEffect(() => {
    if (familyTreeId) {
      console.log(`FamilyTreeVisualization: familyTreeId prop changed to: ${familyTreeId}. Calling loadTreeData.`);
      setActiveNodeDetails(null); // Clear previously selected node
      loadTreeData(familyTreeId);
    } else {
      console.log("FamilyTreeVisualization: familyTreeId is null or undefined. Clearing visualization.");
      if (isMounted.current) {
        setRawData(null);
        setActiveNodeDetails(null);
        setLoading(false);
        setError(null);
      }
    }
  }, [familyTreeId, loadTreeData]); // Added loadTreeData to dependencies

  // Handler for node clicks within the Neo4j graph visualization
  const handleGraphNodeClick = (event) => {
    const { node } = event; // Structure depends on neovis.js-react event format
    if (node && node.properties) {
      console.log('Node clicked in graph:', node);
      const details = {
        id: node.id, // Neo4j internal ID
        name: node.properties.name || 'N/A',
        birthDate: node.properties.birthDate || 'N/A',
        deathDate: node.properties.deathDate || 'N/A',
        // ... other properties from the node
      };
      setActiveNodeDetails(details);
      if (onNodeSelected) {
        onNodeSelected(details); // Pass to parent component
      }
    }
  };

  // Display loading message
  if (loading) {
    return <div className="flex justify-center items-center h-full"><p className="text-gray-600">Loading family tree visualization...</p></div>;
  }

  // Display error message
  if (error) {
    return <div className="flex flex-col justify-center items-center h-full text-red-600">
        <p className="font-semibold">Error rendering family tree:</p>
        <p>{error}</p>
    </div>;
  }

  // If no familyTreeId is provided, prompt user to select one
  if (!familyTreeId) {
    return <div className="flex justify-center items-center h-full"><p className="text-gray-500">Please select a family tree to view.</p></div>;
  }

  // Check for Neo4j connection configuration
  if (!NEO4J_URI || !NEO4J_USER) {
    return (
      <div className="flex flex-col justify-center items-center h-full text-red-700 p-4">
        <h3 className="font-semibold text-lg mb-2">Neo4j Connection Error</h3>
        <p>Neo4j URI or User is not configured.</p>
        <p className="mt-1 text-sm text-gray-600">Please check your environment variables (VITE_NEO4J_URI, VITE_NEO4J_USER).</p>
      </div>
    );
  }

  // Cypher query to fetch data for the specific family tree
  // Assumes Person nodes have a 'tree_id' property matching familyTreeId
  const finalCypherQuery = `
    MATCH (p:Person {tree_id: "${familyTreeId}"})
    OPTIONAL MATCH (p)-[r]-(o:Person {tree_id: "${familyTreeId}"})
    RETURN p, r, o
  `;
  // Note: The relationship part `(p)-[r]-(o)` might return relationships twice if undirected.
  // A common pattern to avoid this is `WHERE id(p) < id(o)`.
  // However, neovis.js might handle this. If you see duplicate edges, refine the query.

  return (
    <div style={containerStyle} className="relative"> {/* Added relative for positioning activeNodeDetails */}
      <ResponsiveNeoGraph
        containerId={`neo4j-graph-vis-${familyTreeId}`} // Unique ID for the graph container
        neo4jUri={NEO4J_URI}
        neo4jUser={NEO4J_USER}
        neo4jPassword={NEO4J_PASSWORD}
        initialCypher={finalCypherQuery}
        onNodeClick={handleGraphNodeClick}
        config={{ // Configuration for neovis.js (passed to vis.js)
          nodes: {
            font: {
              size: 14, // Font size for node labels
              color: '#333'
            },
            shape: 'dot', // Default shape
            size: 18, // Default size
          },
          edges: {
            arrows: {
              to: { enabled: true, scaleFactor: 0.5 } // Show arrows on relationships
            },
            font: {
              size: 10,
              align: 'middle'
            },
            smooth: { // Make edges curved
                type: 'cubicBezier',
                forceDirection: 'horizontal',
                roundness: 0.4
            }
          },
          physics: { // Enable physics for layout
            enabled: true,
            barnesHut: {
              gravitationalConstant: -3000, // Adjust for spread
              springLength: 150, // Adjust for edge length
              springConstant: 0.05,
              damping: 0.09
            },
            minVelocity: 0.75
          },
          interaction: {
            tooltipDelay: 200, // Delay for tooltips
            hover: true // Enable hover effects
          },
          // Define how different node labels are displayed
          nodeClasses: {
            "Person": { // Assuming your nodes have the label "Person"
              label: "name", // Property to use for the node label
              // title: (node) => `Name: ${node.properties.name}\nBorn: ${node.properties.birthDate || 'Unknown'}`, // HTML for tooltip
              // color: '#66ccff', // Example color
              // size: 'importance', // Example: size nodes by an 'importance' property
            }
          },
          // Define how different relationship types are displayed
          relationshipClasses: {
            "RELATED_TO": { // Example relationship type
              // caption: "type", // Property to display on the relationship
              // color: '#848484',
              // dashes: true, // Example: dashed line
            }
          }
        }}
      />
      {activeNodeDetails && (
        <div className="absolute bottom-4 right-4 bg-white p-4 shadow-xl rounded-lg border border-gray-200 w-auto max-w-xs z-10">
          <h3 className="text-base font-semibold mb-2 text-gray-800 border-b pb-1">Selected Person</h3>
          <p className="text-sm text-gray-700"><strong>Name:</strong> {activeNodeDetails.name}</p>
          <p className="text-sm text-gray-700"><strong>Birth Date:</strong> {activeNodeDetails.birthDate}</p>
          {activeNodeDetails.deathDate && activeNodeDetails.deathDate !== 'N/A' && (
            <p className="text-sm text-gray-700"><strong>Death Date:</strong> {activeNodeDetails.deathDate}</p>
          )}
          {/* Add more details as needed */}
        </div>
      )}
    </div>
  );
};

export default FamilyTreeVisualization;
