"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import MapLegend from "@/components/MapLegend";
import MapSidePanel from "@/components/MapSidePanel";

function useWindowSize() {
  const [size, setSize] = useState({ width: 800, height: 600 });
  useEffect(() => {
    const update = () => setSize({ width: window.innerWidth, height: window.innerHeight - 56 });
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return size;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GraphNode {
  id: string;
  routine_type: string | null;
  file_path: string | null;
}

interface GraphLink {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const ROUTINE_TYPE_COLORS: Record<string, string> = {
  driver: "#4a6fa5",       // --chalk-blue
  computational: "#3a8a5c", // --chalk-green
  blas: "#c8860a",          // --chalk-amber
};
const DEFAULT_NODE_COLOR = "#a89e8c"; // --ink-faint

export default function MapPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [routineType, setRoutineType] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const fgRef = useRef<import("react-force-graph-2d").ForceGraphMethods | undefined>(undefined);
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const { width, height } = useWindowSize();

  const fetchGraph = useCallback(async (type?: string) => {
    setLoading(true);
    setError("");
    try {
      const url = type
        ? `${API_URL}/api/graph?routine_type=${encodeURIComponent(type)}`
        : `${API_URL}/api/graph`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setGraphData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load graph");
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph(routineType || undefined);
  }, [routineType, fetchGraph]);

  const handleNodeClick = useCallback((node: { id?: string | number } | null) => {
    if (!node || node.id == null) return;
    const id = String(node.id);
    setSelectedNode((prev) => prev === id ? null : id);
    setHighlightNodes(new Set());
  }, []);

  const handleNodeHover = useCallback((node: unknown) => {
    setHoverNode(node ? (node as GraphNode) : null);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setTooltipPos({ x: e.clientX, y: e.clientY });
  }, []);

  const { gData, degreeMap } = useMemo(() => {
    if (!graphData) return {
      gData: { nodes: [] as GraphNode[], links: [] as { source: GraphNode | string; target: GraphNode | string }[] },
      degreeMap: new Map<string, number>(),
    };
    const nodes = graphData.nodes.map((n) => ({ ...n }));
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const links = graphData.links
      .map((l) => ({
        source: nodeMap.get(l.source) ?? l.source,
        target: nodeMap.get(l.target) ?? l.target,
      }))
      .filter((l) => l.source && l.target);

    const deg = new Map<string, number>();
    for (const l of graphData.links) {
      deg.set(l.source, (deg.get(l.source) || 0) + 1);
      deg.set(l.target, (deg.get(l.target) || 0) + 1);
    }

    return { gData: { nodes, links }, degreeMap: deg };
  }, [graphData]);

  const { callersMap, calleesMap } = useMemo(() => {
    if (!graphData) return { callersMap: new Map<string, string[]>(), calleesMap: new Map<string, string[]>() };
    const callers = new Map<string, string[]>();
    const callees = new Map<string, string[]>();
    for (const l of graphData.links) {
      callees.set(l.source, [...(callees.get(l.source) || []), l.target]);
      callers.set(l.target, [...(callers.get(l.target) || []), l.source]);
    }
    return { callersMap: callers, calleesMap: callees };
  }, [graphData]);

  const neighborSet = useMemo(() => {
    if (!selectedNode) return new Set<string>();
    const s = new Set<string>([selectedNode]);
    for (const c of calleesMap.get(selectedNode) || []) s.add(c);
    for (const c of callersMap.get(selectedNode) || []) s.add(c);
    return s;
  }, [selectedNode, calleesMap, callersMap]);

  const searchSuggestions = useMemo(() => {
    const q = searchQuery.trim().toUpperCase();
    if (!q || !graphData || q.length < 1) return [];
    const seen = new Set<string>();
    const results: string[] = [];
    for (const n of graphData.nodes) {
      if (n.id.includes(q) && !seen.has(n.id)) {
        seen.add(n.id);
        results.push(n.id);
        if (results.length >= 8) break;
      }
    }
    return results;
  }, [searchQuery, graphData]);

  const selectSuggestion = useCallback((id: string) => {
    setSelectedNode(id);
    setSearchQuery("");
    setShowSuggestions(false);
    setHighlightNodes(new Set());
    const node = gData.nodes.find((n) => n.id === id) as (GraphNode & { x?: number; y?: number }) | undefined;
    if (node && fgRef.current && node.x != null && node.y != null) {
      fgRef.current.centerAt(node.x, node.y, 500);
      fgRef.current.zoom(3, 500);
    }
  }, [gData.nodes]);

  const paintNode = useCallback((node: object, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const n = node as GraphNode & { x?: number; y?: number };
    const id = String(n.id ?? "");
    const x = n.x ?? 0;
    const y = n.y ?? 0;
    const degree = degreeMap.get(id) || 0;
    const baseRadius = 3 + Math.min(degree, 30) * (11 / 30);
    const radius = highlightNodes.has(id) ? baseRadius * 1.5 : baseRadius;
    const color = ROUTINE_TYPE_COLORS[n.routine_type || ""] || DEFAULT_NODE_COLOR;
    const isDimmed = selectedNode != null && !neighborSet.has(id);

    // Draw node circle
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.globalAlpha = isDimmed ? 0.12 : 1;
    ctx.fill();
    ctx.globalAlpha = 1;

    // Draw border for selected node
    if (id === selectedNode) {
      ctx.strokeStyle = "#2c2416";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Draw label at high zoom
    if (globalScale > 1.5) {
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${fontSize}px JetBrains Mono, monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#2c2416";
      ctx.globalAlpha = isDimmed ? 0.12 : 0.9;
      ctx.fillText(id, x, y + radius + 1);
      ctx.globalAlpha = 1;
    }
  }, [degreeMap, highlightNodes, selectedNode, neighborSet]);

  if (loading && !graphData) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div
          className="text-sm"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
        >
          Loading call graph…
        </div>
      </main>
    );
  }

  if (error && !graphData) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <p
          className="text-sm"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}
        >
          {error}
        </p>
        <Link
          href="/"
          className="mt-4 text-sm underline"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--chalk-blue)" }}
        >
          Back to search
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col">
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ borderBottom: "2px solid var(--paper-grid)", background: "var(--paper)" }}
      >
        <Link
          href="/"
          className="text-sm"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--chalk-blue)",
          }}
        >
          ← Search
        </Link>
        <h1
          className="text-xl"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--ink)",
          }}
        >
          Library Map
        </h1>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 relative">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (searchSuggestions.length > 0) {
                      selectSuggestion(searchSuggestions[0]);
                    }
                  }
                  if (e.key === "Escape") setShowSuggestions(false);
                }}
                placeholder="Search routine…"
                className="px-2 py-1 rounded text-xs border w-36 sm:w-44"
                style={{
                  fontFamily: "var(--font-jetbrains-mono)",
                  borderColor: "var(--paper-grid)",
                  background: "var(--paper)",
                  color: "var(--ink)",
                }}
              />
              {showSuggestions && searchQuery.trim() && (
                <div
                  className="absolute top-full left-0 mt-1 w-full rounded border z-50 max-h-48 overflow-y-auto"
                  style={{
                    background: "var(--paper)",
                    borderColor: "var(--paper-grid)",
                    boxShadow: "0 4px 12px var(--shadow)",
                  }}
                >
                  {searchSuggestions.length > 0 ? (
                    searchSuggestions.map((id) => (
                      <button
                        key={id}
                        type="button"
                        onMouseDown={() => selectSuggestion(id)}
                        className="w-full text-left px-2 py-1.5 text-xs hover:bg-[var(--paper-dark)] transition-colors cursor-pointer"
                        style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
                      >
                        {id}
                      </button>
                    ))
                  ) : (
                    <div
                      className="px-2 py-1.5 text-xs"
                      style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}
                    >
                      No matching routines
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          <span
            className="text-xs hidden sm:inline"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
          >
            Click a node to explore · Scroll to zoom
          </span>
          <div className="flex items-center gap-2">
            <label
              className="text-xs"
              style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
            >
              Filter:
            </label>
          <select
            value={routineType}
            onChange={(e) => setRoutineType(e.target.value)}
            className="rounded px-2 py-1 text-xs border"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              borderColor: "var(--paper-grid)",
              background: "var(--paper)",
              color: "var(--ink)",
            }}
          >
            <option value="">All</option>
            <option value="driver">Driver</option>
            <option value="computational">Computational</option>
            <option value="blas">BLAS</option>
          </select>
          </div>
        </div>
      </header>

      {/* Tooltip */}
      {hoverNode && (
        <div
          className="fixed z-50 px-3 py-2 rounded text-xs pointer-events-none max-w-xs"
          style={{
            left: Math.min(tooltipPos.x + 12, window.innerWidth - 200),
            top: Math.min(tooltipPos.y + 12, window.innerHeight - 120),
            fontFamily: "var(--font-jetbrains-mono)",
            background: "var(--ink)",
            color: "var(--paper)",
            boxShadow: "0 2px 8px var(--shadow)",
          }}
        >
          <div className="font-bold">{hoverNode.id}</div>
          {hoverNode.routine_type && (
            <div className="text-[10px] opacity-90 mt-0.5">{hoverNode.routine_type}</div>
          )}
          {hoverNode.file_path && (
            <div className="text-[10px] opacity-75 mt-0.5 truncate">{hoverNode.file_path}</div>
          )}
        </div>
      )}

      {/* Graph + Panel */}
      <div className="flex flex-1 min-h-0" style={{ minHeight: "calc(100vh - 56px)" }}>
        <div
          className="flex-1 min-h-0 min-w-0"
          style={{ background: "var(--paper)" }}
          onMouseMove={handleMouseMove}
        >
          {gData.nodes.length > 0 ? (
            <ForceGraph2D
              ref={fgRef}
              graphData={gData}
              nodeId="id"
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(node, color, ctx) => {
                const n = node as GraphNode & { x?: number; y?: number };
                const degree = degreeMap.get(String(n.id ?? "")) || 0;
                const radius = 3 + Math.min(degree, 30) * (11 / 30);
                ctx.beginPath();
                ctx.arc(n.x ?? 0, n.y ?? 0, radius * 1.5, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
              }}
              linkColor={(link) => {
                if (!selectedNode) return "#d4cfc4";
                const s = typeof link.source === "object" ? (link.source as GraphNode).id : link.source;
                const t = typeof link.target === "object" ? (link.target as GraphNode).id : link.target;
                return (neighborSet.has(String(s)) && neighborSet.has(String(t))) ? "#2c2416" : "rgba(212,207,196,0.12)";
              }}
              linkWidth={(link) => {
                if (!selectedNode) return 0.5;
                const s = typeof link.source === "object" ? (link.source as GraphNode).id : link.source;
                const t = typeof link.target === "object" ? (link.target as GraphNode).id : link.target;
                return (neighborSet.has(String(s)) && neighborSet.has(String(t))) ? 1.5 : 0.3;
              }}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              onBackgroundClick={() => setSelectedNode(null)}
              backgroundColor="#faf6ee"
              width={selectedNode ? width - 320 : width}
              height={height}
            />
          ) : (
            <div
              className="flex items-center justify-center h-full text-sm"
              style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
            >
              No nodes to display. Try a different filter.
            </div>
          )}
        </div>

        {selectedNode && graphData && (
          <MapSidePanel
            nodeId={selectedNode}
            routineType={graphData.nodes.find((n) => n.id === selectedNode)?.routine_type ?? null}
            filePath={graphData.nodes.find((n) => n.id === selectedNode)?.file_path ?? null}
            callees={calleesMap.get(selectedNode) || []}
            callers={callersMap.get(selectedNode) || []}
            onNodeSelect={(id) => {
              setSelectedNode(id);
              const node = gData.nodes.find((n) => n.id === id) as (GraphNode & { x?: number; y?: number }) | undefined;
              if (node && fgRef.current && node.x != null && node.y != null) {
                fgRef.current.centerAt(node.x, node.y, 500);
              }
            }}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
      <MapLegend />
    </main>
  );
}
