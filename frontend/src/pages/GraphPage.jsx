import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { getGraph, searchConcepts } from "../utils/api";
import { NODE_COLORS, NODE_RADII, EDGE_COLORS } from "../utils/colors";
import "./Pages.css";

export default function GraphPage({ activeStudent }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [semesterFilter, setSemesterFilter] = useState(0);
  const [showGuide, setShowGuide] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [highlightNodeId, setHighlightNodeId] = useState(null);

  useEffect(() => {
    if (!activeStudent?.student_id) return;
    setLoading(true);
    getGraph(activeStudent.student_id)
      .then((data) => {
        setGraphData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [activeStudent]);

  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3
      .select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    const g = svg.append("g");

    const zoom = d3
      .zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => g.attr("transform", event.transform));

    svg.call(zoom);
    svg.call(
      zoom.transform,
      d3.zoomIdentity.translate(width * 0.08, 30).scale(0.85),
    );

    let nodes = graphData.nodes.map((n) => ({ ...n }));
    let edges = graphData.edges.map((e) => ({ ...e }));

    if (semesterFilter > 0) {
      const semesterIds = new Set(
        nodes.filter((n) => n.semester === semesterFilter).map((n) => n.id),
      );
      edges = edges.filter(
        (e) => semesterIds.has(e.source) || semesterIds.has(e.target),
      );
      const connectedIds = new Set();
      edges.forEach((e) => {
        connectedIds.add(e.source);
        connectedIds.add(e.target);
      });
      nodes = nodes.filter(
        (n) => connectedIds.has(n.id) || n.semester === semesterFilter,
      );
    }

    const rootChains = graphData.root_cause_chains || {};
    const activeEdgePairs = new Set();
    Object.values(rootChains).forEach((chain) => {
      for (let i = 0; i < chain.length - 1; i++) {
        activeEdgePairs.add(`${chain[i]}->${chain[i + 1]}`);
      }
    });

    const rootNodes = new Set();
    Object.values(rootChains).forEach((chain) => {
      if (chain.length > 1) rootNodes.add(chain[chain.length - 1]);
    });

    nodes.forEach((n) => {
      if (rootNodes.has(n.id)) n.state = "root_cause";
    });

    // Build a map for quick radius lookup
    const nodeRadiusMap = {};
    nodes.forEach((n) => {
      nodeRadiusMap[n.id] = NODE_RADII[n.state] || 10;
    });

    const defs = svg.append("defs");

    // Normal arrowhead -- thin, subtle
    defs
      .append("marker")
      .attr("id", "arrow-normal")
      .attr("viewBox", "0 -6 12 12")
      .attr("refX", 12)
      .attr("refY", 0)
      .attr("markerWidth", 7)
      .attr("markerHeight", 7)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L12,0L0,5Z")
      .attr("fill", "#4B5278");

    // Active arrowhead -- red, large
    defs
      .append("marker")
      .attr("id", "arrow-active")
      .attr("viewBox", "0 -6 12 12")
      .attr("refX", 12)
      .attr("refY", 0)
      .attr("markerWidth", 12)
      .attr("markerHeight", 12)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L12,0L0,5Z")
      .attr("fill", "#EF4444");

    // Glow filter
    const glow = defs.append("filter").attr("id", "glow");
    glow
      .append("feGaussianBlur")
      .attr("stdDeviation", 4)
      .attr("result", "blur");
    glow
      .append("feComposite")
      .attr("in", "SourceGraphic")
      .attr("in2", "blur")
      .attr("operator", "over");

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(200)
          .strength((d) => (d.strength ? d.strength * 0.2 : 0.12)),
      )
      .force("charge", d3.forceManyBody().strength(-700).distanceMax(800))
      .force("center", d3.forceCenter(width / 2, height / 2).strength(0.03))
      .force("x", d3.forceX(width / 2).strength(0.025))
      .force(
        "y",
        d3.forceY((d) => (d.semester / 8) * (height - 120) + 60).strength(0.12),
      )
      .force("collision", d3.forceCollide().radius(50).strength(0.9))
      .alpha(0.9)
      .alphaDecay(0.01);

    // -- EDGES as <path> so arrow connects exactly at node boundary --
    const linkGroup = g.append("g").attr("class", "links");

    const link = linkGroup
      .selectAll("path")
      .data(edges)
      .join("path")
      .each(function (d) {
        const srcId = typeof d.source === "object" ? d.source.id : d.source;
        const tgtId = typeof d.target === "object" ? d.target.id : d.target;
        d._isActive = activeEdgePairs.has(`${srcId}->${tgtId}`);
      })
      .attr("fill", "none")
      .attr("stroke", (d) => (d._isActive ? "#EF4444" : "#3D4568"))
      .attr("stroke-width", (d) => (d._isActive ? 2.5 : 0.6))
      .attr("stroke-opacity", (d) => (d._isActive ? 0.95 : 0.22))
      .attr("marker-end", (d) =>
        d._isActive ? "url(#arrow-active)" : "url(#arrow-normal)",
      );

    // -- PARTICLE LAYER for active edges --
    const particleGroup = g.append("g").attr("class", "particles");

    // Draw nodes
    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(
        d3
          .drag()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    // Glow ring for root cause and gap nodes
    node
      .filter((d) => d.state === "root_cause" || d.state === "gap")
      .append("circle")
      .attr("r", (d) => (NODE_RADII[d.state] || 10) + 8)
      .attr("fill", "none")
      .attr("stroke", (d) => (d.state === "root_cause" ? "#EF4444" : "#DC2626"))
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.25)
      .attr("filter", "url(#glow)");

    // Main node circles
    node
      .append("circle")
      .attr("r", (d) => NODE_RADII[d.state] || 10)
      .attr("fill", (d) => NODE_COLORS[d.state] || NODE_COLORS.unassessed)
      .attr("stroke", (d) => {
        if (d.state === "root_cause") return "#FCA5A5";
        if (d.state === "gap") return "#FCA5A5";
        if (d.state === "mastered") return "#86EFAC";
        if (d.state === "decaying") return "#FCD34D";
        return "rgba(255,255,255,0.08)";
      })
      .attr("stroke-width", (d) => {
        if (d.state === "root_cause") return 3;
        if (d.state === "gap") return 2;
        return 1;
      })
      .style("cursor", "pointer");

    // Node labels
    node
      .append("text")
      .text((d) => d.label)
      .attr("dy", (d) => (NODE_RADII[d.state] || 10) + 15)
      .attr("text-anchor", "middle")
      .attr("fill", (d) =>
        d.state === "gap" || d.state === "root_cause" ? "#F1F5F9" : "#94A3B8",
      )
      .attr("font-size", (d) =>
        d.state === "gap" || d.state === "root_cause" ? "11px" : "9px",
      )
      .attr("font-weight", (d) =>
        d.state === "gap" || d.state === "root_cause" ? "600" : "400",
      )
      .attr("font-family", "Inter, sans-serif")
      .attr("paint-order", "stroke")
      .attr("stroke", "#0a0b10")
      .attr("stroke-width", 4)
      .attr("stroke-linejoin", "round");

    // Hover: tooltip + edge highlight
    node
      .on("mouseenter", (event, d) => {
        const rect = container.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left + 14,
          y: event.clientY - rect.top - 14,
          data: d,
        });
        // Highlight connected edges
        link
          .attr("stroke-opacity", (l) => {
            const sid = typeof l.source === "object" ? l.source.id : l.source;
            const tid = typeof l.target === "object" ? l.target.id : l.target;
            if (sid === d.id || tid === d.id) return 1;
            return l._isActive ? 0.5 : 0.1;
          })
          .attr("stroke-width", (l) => {
            const sid = typeof l.source === "object" ? l.source.id : l.source;
            const tid = typeof l.target === "object" ? l.target.id : l.target;
            if (sid === d.id || tid === d.id) return 3;
            return l._isActive ? 2 : 0.5;
          });
      })
      .on("mouseleave", () => {
        setTooltip(null);
        link
          .attr("stroke-opacity", (d) => (d._isActive ? 0.95 : 0.45))
          .attr("stroke-width", (d) => (d._isActive ? 2.5 : 1));
      })
      .on("click", (event, d) => {
        event.stopPropagation();
        const prereqEdges = edges.filter((e) => {
          const sid = typeof e.source === "object" ? e.source.id : e.source;
          return sid === d.id;
        });
        const dependentEdges = edges.filter((e) => {
          const tid = typeof e.target === "object" ? e.target.id : e.target;
          return tid === d.id;
        });
        setSelectedNode({
          ...d,
          prerequisites: prereqEdges
            .map((e) =>
              typeof e.target === "object"
                ? e.target
                : nodes.find((n) => n.id === e.target),
            )
            .filter(Boolean),
          dependents: dependentEdges
            .map((e) =>
              typeof e.source === "object"
                ? e.source
                : nodes.find((n) => n.id === e.source),
            )
            .filter(Boolean),
        });
      });

    // Close panel when clicking on empty space
    svg.on("click", () => setSelectedNode(null));

    // Helper: compute path that stops at the target node's edge
    function computeEdgePath(d) {
      const sx = d.source.x,
        sy = d.source.y;
      const tx = d.target.x,
        ty = d.target.y;
      const dx = tx - sx,
        dy = ty - sy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist === 0) return `M${sx},${sy}L${tx},${ty}`;

      const srcR = nodeRadiusMap[d.source.id] || 10;
      const tgtR = nodeRadiusMap[d.target.id] || 10;

      // Offset for arrowhead: marker refX=12 means tip is at path end.
      // Active arrows have markerWidth=12, normal have markerWidth=7.
      // Path should end tgtR pixels from target center so arrowhead touches node edge.
      const arrowGap = d._isActive ? 2 : 1;

      // Start from edge of source node
      const startX = sx + (dx / dist) * (srcR + 2);
      const startY = sy + (dy / dist) * (srcR + 2);
      // End at edge of target node
      const endX = tx - (dx / dist) * (tgtR + arrowGap);
      const endY = ty - (dy / dist) * (tgtR + arrowGap);

      return `M${startX},${startY}L${endX},${endY}`;
    }

    // -- TICK: update paths and particles --
    let tickCount = 0;
    simulation.on("tick", () => {
      tickCount++;

      // Update edge paths to connect exactly at node boundaries
      link.attr("d", computeEdgePath);

      // Update node positions
      node.attr("transform", (d) => `translate(${d.x},${d.y})`);

      // Spawn particles after simulation settles a bit
      if (tickCount === 80) {
        spawnContinuousParticles(
          particleGroup,
          edges,
          activeEdgePairs,
          nodeRadiusMap,
        );
      }
    });

    return () => simulation.stop();
  }, [graphData, semesterFilter]);

  // Highlight a node when selected from search results
  useEffect(() => {
    if (!highlightNodeId || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    // Find the node group for this concept
    svg.selectAll(".nodes g").each(function (d) {
      if (d.id === highlightNodeId) {
        const nodeG = d3.select(this);
        // Add a pulsing yellow ring
        const ring = nodeG
          .append("circle")
          .attr("r", 30)
          .attr("fill", "none")
          .attr("stroke", "#FBBF24")
          .attr("stroke-width", 3)
          .attr("opacity", 1);
        // Pulse animation
        ring
          .transition()
          .duration(500)
          .attr("r", 40)
          .attr("opacity", 0.6)
          .transition()
          .duration(500)
          .attr("r", 30)
          .attr("opacity", 1)
          .transition()
          .duration(500)
          .attr("r", 40)
          .attr("opacity", 0.6)
          .transition()
          .duration(500)
          .attr("r", 30)
          .attr("opacity", 1)
          .transition()
          .duration(1000)
          .attr("opacity", 0)
          .remove();
      }
    });
  }, [highlightNodeId]);

  if (!activeStudent) {
    return (
      <div className="empty-state">
        <h3>Your Learning Map</h3>
        <p>
          This page shows how all your subjects are connected. Enable Demo Mode
          (top right) to see how gaps in one topic affect others.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="loading-container">
        <span className="spinner" /> Building your knowledge graph...
      </div>
    );
  }

  return (
    <div className="graph-container">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 8,
        }}
      >
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          Knowledge Graph
        </h1>
        <button
          className="btn btn-secondary"
          style={{ fontSize: "0.75rem", padding: "5px 12px" }}
          onClick={() => setShowGuide(!showGuide)}
        >
          {showGuide ? "Hide Guide" : "How to Read"}
        </button>
      </div>

      {showGuide && (
        <div
          className="card"
          style={{
            padding: "14px 18px",
            marginBottom: 12,
            fontSize: "0.82rem",
            lineHeight: 1.8,
            color: "var(--text-secondary)",
          }}
        >
          <strong
            style={{
              color: "var(--text-primary)",
              display: "block",
              marginBottom: 6,
            }}
          >
            Interpreting this graph:
          </strong>
          Each circle is a concept in your curriculum. Arrows point from a
          concept to its prerequisite -- "Linear Regression → Matrix Operations"
          means you need Matrix Operations before learning Linear Regression.
          <br />
          <span style={{ color: "#EF4444", fontWeight: 600 }}>Red nodes</span> =
          knowledge gaps (you scored below 60%).{" "}
          <span style={{ color: "#EF4444", fontWeight: 600 }}>
            Large red nodes with glow
          </span>{" "}
          = root causes (the deepest prerequisite you missed).
          <br />
          <span style={{ color: "#22C55E", fontWeight: 600 }}>Green</span> =
          mastered.{" "}
          <span style={{ color: "#F59E0B", fontWeight: 600 }}>Orange</span> = at
          risk of forgetting.{" "}
          <span style={{ color: "#6B7280", fontWeight: 600 }}>Gray</span> = not
          yet tested.
          <br />
          <span style={{ color: "#EF4444", fontWeight: 600 }}>
            Red moving dots
          </span>{" "}
          = animated particles showing the prerequisite chain from your gap to
          its root cause.
          <br />
          <strong style={{ color: "var(--text-primary)" }}>
            Interactions:
          </strong>{" "}
          Hover to see details. Click a node for a side panel with prerequisites
          and dependents. Drag nodes. Scroll to zoom.
        </div>
      )}

      <div className="graph-controls">
        <select
          value={semesterFilter}
          onChange={(e) => setSemesterFilter(Number(e.target.value))}
          style={{
            padding: "6px 12px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-primary)",
            fontSize: "0.8rem",
          }}
        >
          <option value={0}>All Semesters</option>
          {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
            <option key={s} value={s}>
              Semester {s}
            </option>
          ))}
        </select>

        <div style={{ position: "relative" }}>
          <input
            type="text"
            placeholder="Search any concept..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!e.target.value.trim()) setSearchResults(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && searchQuery.trim()) {
                const gapIds =
                  activeStudent?.gap_areas
                    ?.map((g) => g.concept_id)
                    .join(",") || "";
                searchConcepts(searchQuery, gapIds, 8)
                  .then(setSearchResults)
                  .catch(() => setSearchResults(null));
              }
              if (e.key === "Escape") {
                setSearchResults(null);
                setSearchQuery("");
              }
            }}
            style={{
              padding: "6px 12px",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-primary)",
              fontSize: "0.8rem",
              width: 240,
            }}
          />
          {searchQuery && !searchResults && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                marginTop: 4,
                fontSize: "0.7rem",
                color: "var(--text-tertiary)",
              }}
            >
              Press Enter to search with Hybrid RAG
            </div>
          )}
          {searchResults && searchResults.results && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                width: 320,
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                marginTop: 4,
                zIndex: 30,
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              <div
                style={{
                  padding: "8px 12px",
                  fontSize: "0.7rem",
                  color: "var(--text-tertiary)",
                  borderBottom: "1px solid var(--border)",
                  background: "rgba(255,255,255,0.02)",
                }}
              >
                Found {searchResults.results.length} concepts using Hybrid RAG
                <br />
                (BM25 keyword matching 35% + Neo4j graph traversal 65%)
              </div>
              {searchResults.results.map((r) => (
                <div
                  key={r.concept_id}
                  style={{
                    padding: "10px 12px",
                    fontSize: "0.82rem",
                    borderBottom: "1px solid var(--border)",
                    cursor: "pointer",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background =
                      "rgba(255,255,255,0.04)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "transparent")
                  }
                  onClick={() => {
                    setHighlightNodeId(r.concept_id);
                    setSearchResults(null);
                    setSearchQuery("");
                    // Flash highlight for 3 seconds then clear
                    setTimeout(() => setHighlightNodeId(null), 3000);
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{ textTransform: "capitalize", fontWeight: 500 }}
                    >
                      {r.name || r.concept_id.replace(/_/g, " ")}
                    </span>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        color: "var(--text-tertiary)",
                      }}
                    >
                      Sem {r.semester}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 12,
                      marginTop: 4,
                      fontSize: "0.7rem",
                      color: "var(--text-tertiary)",
                    }}
                  >
                    <span>BM25: {((r.bm25_score || 0) * 100).toFixed(0)}%</span>
                    <span>
                      Graph: {((r.graph_score || 0) * 100).toFixed(0)}%
                    </span>
                    <span style={{ color: "var(--accent)" }}>
                      Combined: {((r.score || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
              {searchResults.results.length === 0 && (
                <div
                  style={{
                    padding: "12px",
                    fontSize: "0.78rem",
                    color: "var(--text-tertiary)",
                  }}
                >
                  No matching concepts. Try "matrix", "regression", or "neural".
                </div>
              )}
            </div>
          )}
        </div>

        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--text-tertiary)",
            marginLeft: 8,
          }}
        >
          {graphData
            ? `${graphData.nodes.length} concepts · ${graphData.edges.length} prerequisites`
            : ""}
        </div>
      </div>

      <div
        className="graph-svg-container"
        ref={containerRef}
        style={{ position: "relative" }}
      >
        <svg ref={svgRef} />

        {tooltip && (
          <div
            className="graph-tooltip"
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            <div className="graph-tooltip-title">{tooltip.data.label}</div>
            <div className="graph-tooltip-row">
              <span>Semester</span>
              <span>{tooltip.data.semester}</span>
            </div>
            <div className="graph-tooltip-row">
              <span>Subject</span>
              <span>{tooltip.data.subject}</span>
            </div>
            <div className="graph-tooltip-row">
              <span>Difficulty</span>
              <span>{tooltip.data.difficulty}/5</span>
            </div>
            <div className="graph-tooltip-row">
              <span>State</span>
              <span
                className={`badge badge-${tooltip.data.state === "root_cause" ? "gap" : tooltip.data.state}`}
              >
                {tooltip.data.state.replace(/_/g, " ")}
              </span>
            </div>
            <div
              style={{
                marginTop: 6,
                fontSize: "0.72rem",
                color: "var(--text-tertiary)",
              }}
            >
              Click for details
            </div>
          </div>
        )}

        {/* Node detail side panel */}
        {selectedNode && (
          <div className="graph-side-panel">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <strong style={{ fontSize: "0.95rem" }}>
                {selectedNode.label}
              </strong>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-tertiary)",
                  cursor: "pointer",
                  fontSize: "1.1rem",
                }}
              >
                ×
              </button>
            </div>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 8,
              }}
            >
              Semester {selectedNode.semester} · {selectedNode.subject} ·
              Difficulty {selectedNode.difficulty}/5
            </div>
            <div style={{ marginBottom: 4 }}>
              <span
                className={`badge badge-${selectedNode.state === "root_cause" ? "gap" : selectedNode.state}`}
              >
                {selectedNode.state.replace(/_/g, " ")}
              </span>
            </div>

            {selectedNode.prerequisites.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "var(--text-tertiary)",
                    marginBottom: 6,
                  }}
                >
                  Requires ({selectedNode.prerequisites.length})
                </div>
                {selectedNode.prerequisites.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      fontSize: "0.8rem",
                      padding: "4px 0",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    {p.label || p.id.replace(/_/g, " ")}
                  </div>
                ))}
              </div>
            )}

            {selectedNode.dependents.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "var(--text-tertiary)",
                    marginBottom: 6,
                  }}
                >
                  Required By ({selectedNode.dependents.length})
                </div>
                {selectedNode.dependents.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      fontSize: "0.8rem",
                      padding: "4px 0",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    {p.label || p.id.replace(/_/g, " ")}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="graph-legend">
          <div className="legend-item">
            <div
              className="legend-dot"
              style={{ background: NODE_COLORS.gap }}
            />{" "}
            Gap
          </div>
          <div className="legend-item">
            <div
              className="legend-dot"
              style={{
                background: NODE_COLORS.root_cause,
                boxShadow: "0 0 6px rgba(239,68,68,0.6)",
              }}
            />{" "}
            Root Cause
          </div>
          <div className="legend-item">
            <div
              className="legend-dot"
              style={{ background: NODE_COLORS.mastered }}
            />{" "}
            Mastered
          </div>
          <div className="legend-item">
            <div
              className="legend-dot"
              style={{ background: NODE_COLORS.decaying }}
            />{" "}
            At Risk
          </div>
          <div className="legend-item">
            <div
              className="legend-dot"
              style={{ background: NODE_COLORS.unassessed }}
            />{" "}
            Unassessed
          </div>
          <div
            className="legend-item"
            style={{
              borderLeft: "1px solid var(--border)",
              paddingLeft: 12,
              gap: 8,
            }}
          >
            <span style={{ color: "#5B6290" }}>→</span> Requires
          </div>
          <div className="legend-item" style={{ gap: 8 }}>
            <span style={{ color: "#EF4444", fontSize: "0.6rem" }}>● ●</span>{" "}
            Root cause chain
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Spawns red animated dots that travel along active (root-cause chain) edges.
 * Each particle is a small SVG circle that moves from source to target along the edge,
 * then loops. This makes the prerequisite chain visible and dynamic.
 */
function spawnContinuousParticles(
  particleGroup,
  edges,
  activeEdgePairs,
  nodeRadiusMap,
) {
  const activeEdges = edges.filter((d) => {
    const srcId = typeof d.source === "object" ? d.source.id : d.source;
    const tgtId = typeof d.target === "object" ? d.target.id : d.target;
    return activeEdgePairs.has(`${srcId}->${tgtId}`);
  });

  if (activeEdges.length === 0) return;

  function launchParticle(edge, delay) {
    setTimeout(() => {
      const sx = typeof edge.source === "object" ? edge.source.x : 0;
      const sy = typeof edge.source === "object" ? edge.source.y : 0;
      const tx = typeof edge.target === "object" ? edge.target.x : 0;
      const ty = typeof edge.target === "object" ? edge.target.y : 0;
      if (sx === 0 && sy === 0) return;

      const srcR = nodeRadiusMap[edge.source.id] || 10;
      const tgtR = nodeRadiusMap[edge.target.id] || 10;

      const dx = tx - sx,
        dy = ty - sy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 10) return;

      const startX = sx + (dx / dist) * srcR;
      const startY = sy + (dy / dist) * srcR;
      const endX = tx - (dx / dist) * tgtR;
      const endY = ty - (dy / dist) * tgtR;

      const particle = particleGroup
        .append("circle")
        .attr("r", 4)
        .attr("fill", "#EF4444")
        .attr("opacity", 0.9)
        .attr("cx", startX)
        .attr("cy", startY)
        .style("filter", "drop-shadow(0 0 3px #EF4444)");

      particle
        .transition()
        .duration(1500)
        .ease(d3.easeLinear)
        .attr("cx", endX)
        .attr("cy", endY)
        .attr("r", 3)
        .attr("opacity", 0.3)
        .remove()
        .on("end", () => {
          // Re-launch from current positions (since nodes may have moved)
          launchParticle(edge, 200);
        });
    }, delay);
  }

  activeEdges.forEach((edge, i) => {
    launchParticle(edge, i * 400);
    // Launch a second wave offset for density
    launchParticle(edge, i * 400 + 800);
  });
}
