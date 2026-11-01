import { useEffect } from "react";
import {
  ReactFlow, Background, Controls, Handle, Position, useNodesState, useEdgesState,
  type Node, type Edge, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const KIND = {
  dataset: "border-sky-500 bg-sky-950 w-56 py-2",
  column: "border-slate-600 bg-slate-900 w-56",
  entity: "border-emerald-500 bg-emerald-950 w-32",
};
const COLOR: Record<string, string> = {
  references: "#38bdf8", semantically_matches: "#a78bfa", derived_from: "#f59e0b",
  conflicts_with: "#ef4444", appears_in: "#34d399", contains: "#334155",
};

function NodeCard({ data, selected }: NodeProps) {
  const d = data as any;
  const n = d.anomalies?.length ?? 0;
  const sub = d.kind === "dataset" ? `${d.rows} rows · quality ${d.quality}`
    : d.kind === "column" ? d.semantic_type : d.status;
  return (
    <div className={`rounded-lg border px-3 py-1.5 text-xs text-slate-100 ${KIND[d.kind as keyof typeof KIND]} ${selected ? "ring-2 ring-amber-400" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="flex justify-between gap-2">
        <span className="truncate font-semibold">{d.label}</span>
        {n > 0 && <span className="text-red-400">⚠ {n}</span>}
      </div>
      <div className="text-slate-400">{sub}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { dataset: NodeCard, column: NodeCard, entity: NodeCard };

export default function GraphView({ graph, onNode, onEdge }: any) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges.map((e: any) => ({
      ...e,
      type: "smoothstep",
      label: e.label === "semantically_matches" ? "" : e.label,
      style: {
        stroke: COLOR[e.label] ?? "#64748b",
        strokeWidth: e.label === "contains" ? 1 : 2,
        strokeDasharray: e.data.provenance === "inferred" ? "6 4" : undefined,
      },
      labelStyle: { fill: "#cbd5e1", fontSize: 10 },
      labelBgStyle: { fill: "#0f172a" },
    })));
  }, [graph, setNodes, setEdges]);

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      onNodeClick={(_, n) => onNode(n.id)}
      onEdgeClick={(_, e) => onEdge(e)}
      colorMode="dark" fitView minZoom={0.2}
    >
      <Background />
      <Controls />
    </ReactFlow>
  );
}