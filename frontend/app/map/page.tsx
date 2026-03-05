"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

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

export default function MapPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [routineType, setRoutineType] = useState("");
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
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
    setHighlightNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleNodeHover = useCallback((node: unknown) => {
    setHoverNode(node ? (node as GraphNode) : null);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setTooltipPos({ x: e.clientX, y: e.clientY });
  }, []);

  const gData = useMemo(() => {
    if (!graphData) return { nodes: [] as GraphNode[], links: [] as { source: GraphNode | string; target: GraphNode | string }[] };
    const nodes = graphData.nodes.map((n) => ({
      ...n,
      val: highlightNodes.has(n.id) ? 12 : 4,
    }));
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const links = graphData.links
      .map((l) => ({
        source: nodeMap.get(l.source) ?? l.source,
        target: nodeMap.get(l.target) ?? l.target,
      }))
      .filter((l) => l.source && l.target);
    return { nodes, links };
  }, [graphData, highlightNodes]);

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
        <div className="flex items-center gap-4">
          <span
            className="text-xs hidden sm:inline"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
          >
            Hover nodes for details · Click to highlight
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

      {/* Graph */}
      <div
        className="flex-1 min-h-0 w-full"
        style={{ background: "var(--paper)", minHeight: "calc(100vh - 56px)" }}
        onMouseMove={handleMouseMove}
      >
        {gData.nodes.length > 0 ? (
          <ForceGraph2D
            graphData={gData}
            nodeId="id"
            nodeColor={(n) =>
              highlightNodes.has(String((n as GraphNode).id ?? ""))
                ? "#c8860a"
                : "#4a6fa5"
            }
            nodeLabel={(n) => {
              const node = n as GraphNode;
              return `${node.id}${node.routine_type ? ` (${node.routine_type})` : ""}`;
            }}
            linkColor="#d4cfc4"
            linkWidth={0.5}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            backgroundColor="#faf6ee"
            width={width}
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
    </main>
  );
}
