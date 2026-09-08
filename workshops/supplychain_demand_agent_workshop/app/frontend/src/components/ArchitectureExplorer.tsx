import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { Workflow } from "lucide-react";
import { fetchArchitecture } from "../useAgentSocket";
import type { ArchitectureGraph } from "../types";
import { useTheme } from "../theme";

interface Props {
  edgeActivity: Record<string, number>;
  nodeActivity: Record<string, number>;
}

const POSITIONS: Record<string, { x: number; y: number }> = {
  user: { x: 0, y: 130 },
  supervisor: { x: 240, y: 130 },
  demand_analyst: { x: 500, y: 40 },
  policy_agent: { x: 500, y: 220 },
  oracle_vs: { x: 800, y: 130 },
  agent_store: { x: 800, y: 260 },
  saver: { x: 240, y: 280 },
};

interface PaletteStyle {
  bg: string;
  border: string;
  color: string;
}

const KIND_STYLE_DARK: Record<string, PaletteStyle> = {
  user: { bg: "#1a1a1a", border: "#2f2f2f", color: "#e0e0e0" },
  supervisor: { bg: "#f80000", border: "#cc0000", color: "#fff" },
  specialist: { bg: "#118ab2", border: "#0e7290", color: "#fff" },
  store: { bg: "#06d6a0", border: "#0a8e6b", color: "#0a0a0a" },
};
const KIND_STYLE_LIGHT: Record<string, PaletteStyle> = {
  user: { bg: "#f3f4f6", border: "#d1d5db", color: "#111827" },
  supervisor: { bg: "#f80000", border: "#a30000", color: "#fff" },
  specialist: { bg: "#0c7da6", border: "#075a78", color: "#fff" },
  store: { bg: "#0aa37a", border: "#076d52", color: "#fff" },
};

const ACTIVE_MS = 2200;

function ArchitectureInner({ edgeActivity, nodeActivity }: Props) {
  const { theme } = useTheme();
  const [graph, setGraph] = useState<ArchitectureGraph | null>(null);
  const [tick, setTick] = useState(0);
  const fitDoneRef = useRef(false);
  const rf = useReactFlow();

  useEffect(() => {
    fetchArchitecture()
      .then(setGraph)
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (graph && !fitDoneRef.current) {
      const id = setTimeout(() => {
        try {
          rf.fitView({ padding: 0.2 });
        } catch {
          /* no-op */
        }
        fitDoneRef.current = true;
      }, 80);
      return () => clearTimeout(id);
    }
  }, [graph, rf]);

  useEffect(() => {
    const stamps = [...Object.values(nodeActivity), ...Object.values(edgeActivity)];
    if (stamps.length === 0) return;
    const latest = Math.max(...stamps);
    const remaining = latest + ACTIVE_MS - Date.now();
    if (remaining <= 0) return;
    const id = setTimeout(() => setTick((t) => t + 1), remaining + 50);
    return () => clearTimeout(id);
  }, [nodeActivity, edgeActivity]);

  const palette = theme === "dark" ? KIND_STYLE_DARK : KIND_STYLE_LIGHT;
  const dimEdge = theme === "dark" ? "#3a3a3a" : "#c5c9cf";
  const labelFill = theme === "dark" ? "#888" : "#525252";
  const labelBgFill = theme === "dark" ? "#0a0a0a" : "#ffffff";
  const activeColor = theme === "dark" ? "#ffd166" : "#b45309"; // amber-700 stays readable on white
  const activeGlow =
    theme === "dark" ? "0 0 0 3px rgba(255, 209, 102, 0.35)" : "0 0 0 3px rgba(180, 83, 9, 0.30)";

  const now = Date.now();

  const nodes: Node[] = useMemo(() => {
    if (!graph) return [];
    return graph.nodes.map((n) => {
      const age = now - (nodeActivity[n.id] || 0);
      const active = age < ACTIVE_MS;
      const s = palette[n.kind] || palette.user;
      return {
        id: n.id,
        type: "default",
        position: POSITIONS[n.id] || { x: 0, y: 0 },
        data: { label: n.label },
        style: {
          background: s.bg,
          border: `1px solid ${active ? activeColor : s.border}`,
          color: s.color,
          padding: 8,
          borderRadius: 6,
          fontSize: 11,
          fontFamily: "JetBrains Mono, Menlo, monospace",
          minWidth: 130,
          boxShadow: active ? activeGlow : "none",
          transition: "box-shadow 0.3s ease, border-color 0.3s ease",
        },
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, nodeActivity, tick, theme]);

  const edges: Edge[] = useMemo(() => {
    if (!graph) return [];
    return graph.edges.map((e) => {
      const age = now - (edgeActivity[e.id] || 0);
      const active = age < ACTIVE_MS;
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: active,
        markerEnd: { type: MarkerType.ArrowClosed, color: active ? activeColor : dimEdge },
        style: {
          stroke: active ? activeColor : dimEdge,
          strokeWidth: active ? 2.5 : 1.5,
          strokeDasharray: e.dashed ? "6 6" : undefined,
        },
        labelStyle: { fontSize: 10, fill: labelFill, fontFamily: "JetBrains Mono, monospace" },
        labelBgStyle: { fill: labelBgFill, fillOpacity: 0.7 },
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, edgeActivity, tick, theme]);

  const onInit = useCallback(() => {
    /* fitView handled by effect */
  }, []);

  if (!graph) {
    return (
      <div className="h-full grid place-items-center text-text-muted text-xs">
        loading architecture…
      </div>
    );
  }

  const bgColor = theme === "dark" ? "#080808" : "#ffffff";
  const gridColor = theme === "dark" ? "#1a1a1a" : "#e6e8eb";

  return (
    <div style={{ width: "100%", height: "100%", background: bgColor }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onInit={onInit}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll={false}
        zoomOnScroll
        minZoom={0.4}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color={gridColor} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export function ArchitectureExplorer({ edgeActivity, nodeActivity }: Props) {
  return (
    <div className="pane h-full">
      <div className="pane-header">
        <div className="flex items-center gap-2">
          <Workflow size={13} className="text-accent-skill" />
          <div className="pane-title">Architecture explorer</div>
        </div>
        <div className="text-[10px] text-text-muted">
          edges + nodes light up when their tool fires
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ReactFlowProvider>
          <ArchitectureInner edgeActivity={edgeActivity} nodeActivity={nodeActivity} />
        </ReactFlowProvider>
      </div>
    </div>
  );
}
