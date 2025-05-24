import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

// Helper function to generate a simple gender icon path
const getGenderIconPath = (gender) => {
  if (gender === 'male') {
    return 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-2.5-11h2v2.5h2.5v2h-2.5V16h-2v-2.5H7v-2h2.5V9z'; // Simple male symbol (circle with arrow)
  } else if (gender === 'female') {
    return 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1 2.5V20h2v-2.5c1.93 0 3.5-1.57 3.5-3.5S14.93 10.5 13 10.5s-3.5 1.57-3.5 3.5S10.07 16.5 12 16.5z M12 6c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'; // Simple female symbol (circle with cross)
  }
  return ''; // No icon for other/unknown
};

const D3FamilyTreeVisualization = ({ treeData, onNodeClick, width, height }) => {
  const svgRef = useRef();
  const [tooltip, setTooltip] = useState({ visible: false, content: '', x: 0, y: 0 });

  useEffect(() => {
    if (!treeData || !treeData.nodes || !treeData.links || !width || !height) {
      // Clear SVG if no data or dimensions
      if (svgRef.current) {
        d3.select(svgRef.current).selectAll("*").remove();
      }
      return;
    }

    const { nodes: initialNodes, links: initialLinks } = treeData;

    // Deep copy nodes and links to avoid mutating props, D3 simulation modifies these
    const nodes = JSON.parse(JSON.stringify(initialNodes));
    const links = JSON.parse(JSON.stringify(initialLinks));

    // Map links to use node objects if source/target are IDs
    // D3 forceLink works with IDs if .id() accessor is provided, or with indices.
    // For stability, ensure links reference the node objects from our 'nodes' array.
    const nodeById = new Map(nodes.map(node => [node.id, node]));
    links.forEach(link => {
        link.source = nodeById.get(link.source) || link.source;
        link.target = nodeById.get(link.target) || link.target;
    });


    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous rendering

    const svgElement = svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet");

    const zoomGroup = svgElement.append("g").attr("class", "zoom-group");

    // Define arrow marker for directed links (e.g., parent-child)
    zoomGroup.append("defs").append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 28) // Arrow position relative to node edge
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#777");

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links)
        .id(d => d.id)
        .distance(d => (d.data?.relationship_type?.toLowerCase().includes('spouse')) ? 80 : 180) // Shorter for spouses
        .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-800)) // Increased repulsion for less overlap
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(75).strength(0.7)); // Collision radius based on node size

    const linkElements = zoomGroup.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", d => (d.data?.relationship_type?.toLowerCase().includes('spouse')) ? 3 : 1.5)
      .attr("stroke", d => (d.data?.relationship_type?.toLowerCase().includes('spouse')) ? "#888" : "#bbb")
      .attr("stroke-opacity", 0.8)
      .attr("marker-end", d => (d.data?.relationship_type?.toLowerCase().includes('parent')) ? "url(#arrow)" : null);

    const nodeElements = zoomGroup.append("g")
      .attr("class", "nodes")
      .selectAll("g.node-group")
      .data(nodes, d => d.id)
      .join("g")
      .attr("class", "node-group")
      .style("cursor", "pointer")
      .call(drag(simulation))
      .on("click", (event, d) => {
        if (onNodeClick) {
          onNodeClick(d); // Pass the original node data object
        }
      })
      .on("mouseover", (event, d) => {
        d3.select(event.currentTarget).select("rect").attr("stroke", "#3498db").attr("stroke-width", 3);
        const [x, y] = d3.pointer(event, svgElement.node());
        setTooltip({
          visible: true,
          content: `
            <strong>${d.data.name || 'Unknown'}</strong><br/>
            Gender: ${d.data.gender || 'N/A'}<br/>
            Born: ${d.data.birth_date || 'N/A'}<br/>
            Died: ${d.data.death_date || 'N/A'}
          `,
          x: x + 15,
          y: y - 10,
        });
      })
      .on("mouseout", (event, d) => {
        d3.select(event.currentTarget).select("rect").attr("stroke", "#999").attr("stroke-width", 1.5);
        setTooltip({ visible: false, content: '', x: 0, y: 0 });
      });

    // Node appearance (Rectangular cards)
    const nodeWidth = 140;
    const nodeHeight = 70;
    const avatarRadius = 20;

    nodeElements.append("rect")
      .attr("width", nodeWidth)
      .attr("height", nodeHeight)
      .attr("x", -nodeWidth / 2)
      .attr("y", -nodeHeight / 2)
      .attr("rx", 8)
      .attr("ry", 8)
      .attr("fill", "#ffffff")
      .attr("stroke", "#999")
      .attr("stroke-width", 1.5)
      .style("filter", "drop-shadow(0px 2px 4px rgba(0,0,0,0.1))");

    // Avatar placeholder (circle with initials)
    nodeElements.append("circle")
      .attr("cx", -nodeWidth / 2 + avatarRadius + 10)
      .attr("cy", 0)
      .attr("r", avatarRadius)
      .attr("fill", d => d.data.gender === 'male' ? '#d1e9ff' : (d.data.gender === 'female' ? '#ffe4e1' : '#e0e0e0'))
      .attr("stroke", d => d.data.gender === 'male' ? '#74b9ff' : (d.data.gender === 'female' ? '#fab1a0' : '#bdbdbd'))
      .attr("stroke-width", 1.5);

    nodeElements.append("text")
      .attr("class", "initials")
      .attr("x", -nodeWidth / 2 + avatarRadius + 10)
      .attr("y", 0)
      .attr("dy", "0.35em")
      .attr("text-anchor", "middle")
      .style("font-size", "16px")
      .style("font-weight", "bold")
      .style("fill", d => d.data.gender === 'male' ? '#0984e3' : (d.data.gender === 'female' ? '#d63031' : '#555'))
      .text(d => {
        const name = d.data.name || "";
        const parts = name.split(" ");
        if (parts.length > 1) {
          return (parts[0][0] || "") + (parts[parts.length - 1][0] || "");
        } else if (parts.length === 1 && parts[0].length > 0) {
          return parts[0][0];
        }
        return "?";
      });
      
    // Name text
    nodeElements.append("text")
      .attr("class", "name-label")
      .attr("x", avatarRadius - 10) // Position next to avatar
      .attr("y", -nodeHeight / 2 + 25)
      .attr("text-anchor", "start")
      .style("font-size", "13px")
      .style("font-weight", "600")
      .style("fill", "#333")
      .text(d => (d.data.name || 'Unknown').length > 15 ? (d.data.name || 'Unknown').substring(0, 13) + '...' : (d.data.name || 'Unknown'));

    // Birth date text
    nodeElements.append("text")
      .attr("class", "details-label")
      .attr("x", avatarRadius - 10)
      .attr("y", -nodeHeight / 2 + 45)
      .attr("text-anchor", "start")
      .style("font-size", "10px")
      .style("fill", "#666")
      .text(d => `Born: ${d.data.birth_date || 'N/A'}`);


    simulation.on("tick", () => {
      linkElements
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      nodeElements
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag functionality
    function drag(simulationInstance) {
      function dragstarted(event, d) {
        if (!event.active) simulationInstance.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }
      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }
      function dragended(event, d) {
        if (!event.active) simulationInstance.alphaTarget(0);
        d.fx = null; // Let simulation take over again for x
        d.fy = null; // Let simulation take over again for y
      }
      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }

    // Zoom functionality
    const zoomHandler = d3.zoom()
      .scaleExtent([0.2, 3]) // Min/max zoom levels
      .on("zoom", (event) => {
        zoomGroup.attr("transform", event.transform);
      });
    svgElement.call(zoomHandler);
    
    // Set initial zoom to fit content (optional, can be tricky with dynamic layouts)
    // For now, let it start at default zoom centered.

    // Cleanup simulation on component unmount
    return () => {
      simulation.stop();
    };

  }, [treeData, onNodeClick, width, height]); // Rerun effect if data, callbacks or dimensions change

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <svg ref={svgRef} style={{ width: '100%', height: '100%' }}></svg>
      {tooltip.visible && (
        <div
          style={{
            position: 'absolute',
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            background: 'rgba(0, 0, 0, 0.8)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            pointerEvents: 'none', // Allow interaction with elements underneath
            transform: 'translateY(-100%)', // Position above cursor
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
            whiteSpace: 'nowrap',
          }}
          dangerouslySetInnerHTML={{ __html: tooltip.content }}
        />
      )}
    </div>
  );
};

export default D3FamilyTreeVisualization;
