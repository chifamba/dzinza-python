// src/components/FamilyTreeVisualization.jsx
import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import NeoVis from 'neovis.js'; // Corrected import to use the installed 'neovis.js'
import api from '../api'; // Import api from api.js

const FamilyTreeVisualization = ({ initialCypher }) => {
  const visRef = useRef(null);
  const visInstanceRef = useRef(null); // Ref to store the NeoVis instance for cleanup
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // Effect for fetching initial data or performing pre-checks
  useEffect(() => {
    const loadPrerequisites = async () => {
      try {
        setLoading(true);
        // Assuming getFamilyTreeGraph is a general check or setup step.
        // If its result is needed to construct initialCypher or for NeoVis config,
        // this logic would need to be adjusted.
        await api.getTreeData(); // Fetch tree data from the API
        setError(null); // Clear previous errors if any
      } catch (err) {
        console.error("Failed to fetch family tree data or prerequisites:", err);
        setError(err.message || 'Failed to load prerequisite data.');
      } finally {
        setLoading(false);
      }
    };

    loadPrerequisites();
  }, []); // Runs once on mount

  // Effect for initializing and rendering NeoVis
  useEffect(() => {
    // Ensure the component is mounted, not loading, no errors, and container ref is available
    if (visRef.current && !loading && !error) {
      const config = {
        containerId: visRef.current.id,
        neo4j: {
          serverUrl: import.meta.env.VITE_NEO4J_URI,
          serverUser: import.meta.env.VITE_NEO4J_USER,
          serverPassword: import.meta.env.VITE_NEO4J_PASSWORD,
        },
        // visConfig structure might be specific to your neovis.js version.
        // Consult neovis.js documentation if issues arise with these options.
        visConfig: { 
          arrows: true,
          hierarchical: false,
        },
        initialCypher: initialCypher || 'MATCH (p:Person)-[r]->(o) RETURN p, r, o LIMIT 100',
        labels: {
          "Person": { 
            label: "name", 
            title: (node) => { 
                let tooltipContent = `<p class="font-semibold text-lg mb-1">${node.properties.name || 'N/A'}</p>`;
                if (node.properties.gender) tooltipContent += `<p><strong>Gender:</strong> ${node.properties.gender}</p>`;
                if (node.properties.birthDate) tooltipContent += `<p><strong>Birth Date:</strong> ${node.properties.birthDate}</p>`;
                if (node.properties.deathDate) tooltipContent += `<p><strong>Death Date:</strong> ${node.properties.deathDate}</p>`;
                if (node.properties.occupation) tooltipContent += `<p><strong>Occupation:</strong> ${node.properties.occupation}</p>`;
                return tooltipContent;
            },
            size: 1, 
          }
        },
        relationships: { 
            "CHILD_OF": {
                caption: false, 
                thickness: 1.5,
                color: "#77AADD" 
            },
            "MARRIED_TO": {
                caption: false,
                thickness: 1.5,
                color: "#FF8888" 
            },
            "SIBLING_OF": {
                caption: false,
                thickness: 1.5,
                color: "#88DD88" 
            }
        },
      };

      // Clear previous visualization if any
      if (visInstanceRef.current && typeof visInstanceRef.current.clear === 'function') {
        visInstanceRef.current.clear();
      } else if (visRef.current) { 
        while (visRef.current.firstChild) {
          visRef.current.removeChild(visRef.current.firstChild);
        }
      }
      
      try {
        const viz = new NeoVis(config);
        viz.render();
        visInstanceRef.current = viz; // Store instance for cleanup
      } catch (visError) {
        console.error("NeoVis rendering error:", visError);
        setError(prevError => {
            const newError = "Failed to render visualization: " + visError.message;
            return prevError ? prevError + "; " + newError : newError;
        });
      }
    }

    // Cleanup function
    return () => {
      if (visInstanceRef.current) {
        if (typeof visInstanceRef.current.clear === 'function') {
          visInstanceRef.current.clear();
        } else if (typeof visInstanceRef.current.destroy === 'function') {
          visInstanceRef.current.destroy();
        } else if (visInstanceRef.current._network && typeof visInstanceRef.current._network.destroy === 'function') {
            visInstanceRef.current._network.destroy();
        }
        visInstanceRef.current = null;
      }
      if (visRef.current) {
        while (visRef.current.firstChild) {
          visRef.current.removeChild(visRef.current.firstChild);
        }
      }
    };
  }, [initialCypher, loading, error]); // Rerun when these change

  if (loading) {
    return <div className="flex justify-center items-center h-[600px] text-lg">Loading family tree visualization...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600 bg-red-100 border border-red-400 rounded-md h-[600px]">
        <p className="font-semibold">Error loading visualization:</p>
        <p>{error}</p>
    </div>;
  }

  return (
    <div 
        id="family-tree-vis-container" 
        ref={visRef} 
        className="w-full h-[600px] border border-gray-300 rounded-lg shadow-lg bg-gray-50"
        aria-label="Family Tree Visualization Area"
        role="img" 
    />
  );
};

FamilyTreeVisualization.propTypes = {
  initialCypher: PropTypes.string,
};

export default FamilyTreeVisualization;
