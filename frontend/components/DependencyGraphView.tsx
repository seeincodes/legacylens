"use client";

import { useMemo } from "react";
import { ReactFlow, useNodesState, useEdgesState } from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

interface DependencyNode {
  name: string;
  routine_type: string | null;
  file_path: string | null;
  calls: string[];
  depth: number;
}

interface DependencyData {
  root: string;
  nodes: DependencyNode[];
  max_depth: number;
}

function getLayoutedElements(nodes: DependencyNode[]) {
  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 60 });

  const nodeIds = new Set<string>();
  const edges: { source: string; target: string }[] = [];

  for (const node of nodes) {
    const id = node.name;
    nodeIds.add(id);
    g.setNode(id, { width: 140, height: 44 });
    for (const callee of node.calls) {
      if (nodes.some((n) => n.name === callee)) {
        edges.push({ source: id, target: callee });
        g.setEdge(id, callee);
      }
    }
  }

  dagre.layout(g);

  const flowNodes = Array.from(nodeIds).map((id) => {
    const node = g.node(id);
    return {
      id,
      type: "default",
      position: { x: node.x - 70, y: node.y - 22 },
      data: { label: id },
    };
  });

  const flowEdges = edges.map((e, i) => ({
    id: `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

interface DependencyGraphViewProps {
  data: DependencyData;
}

export default function DependencyGraphView({ data }: DependencyGraphViewProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => getLayoutedElements(data.nodes),
    [data.nodes]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="w-full h-[320px] rounded-lg overflow-hidden border" style={{ borderColor: "var(--paper-grid)", background: "var(--paper)" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        style={{
          "--xyflow-background-color": "var(--paper)",
          "--xyflow-node-background-color": "var(--paper)",
        } as React.CSSProperties}
      />
    </div>
  );
}
