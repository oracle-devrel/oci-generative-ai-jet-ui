"use client";

import {
  useState,
  useCallback,
  useRef,
  useEffect,
  useMemo,
} from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface MCTSNode {
  id: string;
  label: string;
  wins: number;
  visits: number;
  children: MCTSNode[];
  parentId: string | null;
  depth: number;
}

type MCTSPhase =
  | "idle"
  | "selection"
  | "expansion"
  | "simulation"
  | "backpropagation";

interface SimResult {
  win: boolean;
  path: string[];         // node IDs on the selected path
  expandedNodeId: string | null;
  rolloutResult: boolean;
}

/* ------------------------------------------------------------------ */
/*  UCB1 calculation                                                   */
/* ------------------------------------------------------------------ */

function ucb1(wins: number, visits: number, parentVisits: number, C: number): number {
  if (visits === 0) return Infinity;
  return wins / visits + C * Math.sqrt(Math.log(parentVisits) / visits);
}

function ucb1Display(wins: number, visits: number, parentVisits: number, C: number): string {
  if (visits === 0) return "\u221e";
  const val = wins / visits + C * Math.sqrt(Math.log(parentVisits) / visits);
  return val.toFixed(2);
}

/* ------------------------------------------------------------------ */
/*  Deep-clone tree                                                    */
/* ------------------------------------------------------------------ */

function cloneTree(node: MCTSNode): MCTSNode {
  return {
    ...node,
    children: node.children.map(cloneTree),
  };
}

/* ------------------------------------------------------------------ */
/*  Build initial tree                                                 */
/* ------------------------------------------------------------------ */

function buildInitialTree(): MCTSNode {
  const root: MCTSNode = {
    id: "root",
    label: "Root",
    wins: 15,
    visits: 30,
    children: [],
    parentId: null,
    depth: 0,
  };

  const childA: MCTSNode = {
    id: "a",
    label: "Move A",
    wins: 8,
    visits: 15,
    children: [],
    parentId: "root",
    depth: 1,
  };

  const childB: MCTSNode = {
    id: "b",
    label: "Move B",
    wins: 5,
    visits: 10,
    children: [],
    parentId: "root",
    depth: 1,
  };

  const childC: MCTSNode = {
    id: "c",
    label: "Move C",
    wins: 2,
    visits: 5,
    children: [],
    parentId: "root",
    depth: 1,
  };

  root.children = [childA, childB, childC];
  return root;
}

/* ------------------------------------------------------------------ */
/*  Find node by id                                                    */
/* ------------------------------------------------------------------ */

function findNode(root: MCTSNode, id: string): MCTSNode | null {
  if (root.id === id) return root;
  for (const c of root.children) {
    const found = findNode(c, id);
    if (found) return found;
  }
  return null;
}

/* ------------------------------------------------------------------ */
/*  Collect all nodes as flat list                                     */
/* ------------------------------------------------------------------ */

function flattenTree(root: MCTSNode): MCTSNode[] {
  const result: MCTSNode[] = [root];
  for (const c of root.children) {
    result.push(...flattenTree(c));
  }
  return result;
}

/* ------------------------------------------------------------------ */
/*  Seeded pseudo-random                                               */
/* ------------------------------------------------------------------ */

function makeRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

/* ------------------------------------------------------------------ */
/*  Move label bank                                                    */
/* ------------------------------------------------------------------ */

const MOVE_LABELS = [
  "Flank L", "Flank R", "Push Mid", "Defend",
  "Scout", "Ambush", "Retreat", "Advance",
  "Hold", "Strike", "Feint", "Siege",
  "Rush", "Fortify", "Regroup", "Charge",
  "Encircle", "Probe", "Reinforce", "Divert",
  "Pin", "Sweep", "Blitz", "Counter",
];

/* ------------------------------------------------------------------ */
/*  MCTS step logic: select best leaf using UCB1                       */
/* ------------------------------------------------------------------ */

function selectBestLeaf(root: MCTSNode, C: number): string[] {
  const path: string[] = [root.id];
  let current = root;

  while (current.children.length > 0) {
    let bestChild = current.children[0];
    let bestUcb = -Infinity;
    for (const child of current.children) {
      const u = ucb1(child.wins, child.visits, current.visits, C);
      if (u > bestUcb) {
        bestUcb = u;
        bestChild = child;
      }
    }
    path.push(bestChild.id);
    current = bestChild;
  }

  return path;
}

/* ------------------------------------------------------------------ */
/*  Layout: position nodes in SVG                                      */
/* ------------------------------------------------------------------ */

interface PositionedNode {
  node: MCTSNode;
  x: number;
  y: number;
}

function layoutMCTS(
  root: MCTSNode,
  svgWidth: number,
  svgHeight: number,
): Map<string, { x: number; y: number }> {
  const posMap = new Map<string, { x: number; y: number }>();

  // BFS to collect levels
  const levels: MCTSNode[][] = [];
  const queue: MCTSNode[] = [root];
  while (queue.length > 0) {
    const size = queue.length;
    const level: MCTSNode[] = [];
    for (let i = 0; i < size; i++) {
      const node = queue.shift()!;
      level.push(node);
      for (const child of node.children) {
        queue.push(child);
      }
    }
    levels.push(level);
  }

  const yPad = 50;
  const totalDepth = levels.length;
  const yStep = totalDepth > 1 ? (svgHeight - yPad * 2) / (totalDepth - 1) : 0;

  for (let d = 0; d < levels.length; d++) {
    const level = levels[d];
    const count = level.length;
    const xPad = 50;
    const usable = svgWidth - xPad * 2;
    const xStep = count > 1 ? usable / (count - 1) : 0;

    for (let i = 0; i < count; i++) {
      posMap.set(level[i].id, {
        x: count > 1 ? xPad + i * xStep : svgWidth / 2,
        y: yPad + d * yStep,
      });
    }
  }

  return posMap;
}

/* ------------------------------------------------------------------ */
/*  Max depth helper                                                   */
/* ------------------------------------------------------------------ */

function maxDepth(root: MCTSNode): number {
  if (root.children.length === 0) return root.depth;
  return Math.max(...root.children.map(maxDepth));
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function MCTSWidget() {
  /* Hydration guard */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* Core state */
  const [tree, setTree] = useState<MCTSNode>(() => buildInitialTree());
  const [simCount, setSimCount] = useState(0);
  const maxSims = 20;

  /* Phase animation state */
  const [phase, setPhase] = useState<MCTSPhase>("idle");
  const [selectionPath, setSelectionPath] = useState<string[]>([]);
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);
  const [rolloutResult, setRolloutResult] = useState<boolean | null>(null);
  const [backpropIds, setBackpropIds] = useState<string[]>([]);
  const [flashingIds, setFlashingIds] = useState<Set<string>>(new Set());

  /* Config */
  const [explorationC, setExplorationC] = useState(1.414);

  /* Running state for 5x */
  const runningRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const simSeedRef = useRef(42);

  /* Cleanup */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      runningRef.current = false;
    };
  }, []);

  /* SVG dimensions */
  const treeDepth = useMemo(() => maxDepth(tree), [tree]);
  const svgWidth = 580;
  const svgHeight = Math.max(300, (treeDepth + 1) * 130 + 80);

  /* Position map */
  const posMap = useMemo(
    () => layoutMCTS(tree, svgWidth, svgHeight),
    [tree, svgWidth, svgHeight],
  );

  /* Flat nodes for rendering */
  const allNodes = useMemo(() => flattenTree(tree), [tree]);

  /* ---------------------------------------------------------------- */
  /*  Run a single MCTS cycle                                          */
  /* ---------------------------------------------------------------- */

  const runOneCycle = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      const rng = makeRng(simSeedRef.current++);

      // --- Phase 1: Selection ---
      setPhase("selection");
      const path = selectBestLeaf(tree, explorationC);
      setSelectionPath(path);
      setExpandedNodeId(null);
      setRolloutResult(null);
      setBackpropIds([]);
      setFlashingIds(new Set());

      timerRef.current = setTimeout(() => {
        // --- Phase 2: Expansion ---
        setPhase("expansion");

        const leafId = path[path.length - 1];
        const newTree = cloneTree(tree);
        const leafNode = findNode(newTree, leafId)!;

        // Determine new node id and label
        const existingCount = flattenTree(newTree).length;
        const newId = `n${existingCount}`;
        const labelIdx = (existingCount - 1) % MOVE_LABELS.length;
        const newChild: MCTSNode = {
          id: newId,
          label: MOVE_LABELS[labelIdx],
          wins: 0,
          visits: 0,
          children: [],
          parentId: leafId,
          depth: leafNode.depth + 1,
        };

        leafNode.children.push(newChild);
        setTree(newTree);
        setExpandedNodeId(newId);

        // Update path to include new node
        const expandedPath = [...path, newId];
        setSelectionPath(expandedPath);

        timerRef.current = setTimeout(() => {
          // --- Phase 3: Simulation ---
          setPhase("simulation");
          const win = rng() > 0.45; // slightly biased toward wins
          setRolloutResult(win);

          timerRef.current = setTimeout(() => {
            // --- Phase 4: Backpropagation ---
            setPhase("backpropagation");
            setBackpropIds(expandedPath);

            // Flash each node in path in reverse
            const flashTree = cloneTree(newTree);
            const winValue = win ? 1 : 0;

            // Update all nodes on the path
            for (const nodeId of expandedPath) {
              const n = findNode(flashTree, nodeId)!;
              n.visits += 1;
              n.wins += winValue;
            }

            // Animate flash: show flashing IDs
            setFlashingIds(new Set(expandedPath));
            setTree(flashTree);

            timerRef.current = setTimeout(() => {
              setFlashingIds(new Set());
              setPhase("idle");
              setSimCount((prev) => prev + 1);
              setSelectionPath([]);
              setExpandedNodeId(null);
              setRolloutResult(null);
              setBackpropIds([]);
              resolve();
            }, 500);
          }, 500);
        }, 500);
      }, 500);
    });
  }, [tree, explorationC]);

  /* ---------------------------------------------------------------- */
  /*  Run simulation button                                            */
  /* ---------------------------------------------------------------- */

  const handleRunOne = useCallback(async () => {
    if (phase !== "idle" || simCount >= maxSims) return;
    await runOneCycle();
  }, [phase, simCount, runOneCycle]);

  /* ---------------------------------------------------------------- */
  /*  Run 5x                                                           */
  /* ---------------------------------------------------------------- */

  const handleRun5x = useCallback(async () => {
    if (phase !== "idle" || simCount >= maxSims) return;
    runningRef.current = true;
    const remaining = Math.min(5, maxSims - simCount);
    for (let i = 0; i < remaining; i++) {
      if (!runningRef.current) break;
      await runOneCycle();
    }
    runningRef.current = false;
  }, [phase, simCount, runOneCycle]);

  /* ---------------------------------------------------------------- */
  /*  Reset                                                            */
  /* ---------------------------------------------------------------- */

  const handleReset = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    runningRef.current = false;
    setTree(buildInitialTree());
    setSimCount(0);
    setPhase("idle");
    setSelectionPath([]);
    setExpandedNodeId(null);
    setRolloutResult(null);
    setBackpropIds([]);
    setFlashingIds(new Set());
    simSeedRef.current = 42;
  }, []);

  /* ---------------------------------------------------------------- */
  /*  UCB1 values for display in formula                               */
  /* ---------------------------------------------------------------- */

  const selectedLeafForFormula = useMemo(() => {
    if (selectionPath.length < 2) return null;
    // The last child before the leaf (or the leaf itself if no expansion yet)
    const targetId = expandedNodeId
      ? selectionPath[selectionPath.length - 2]
      : selectionPath[selectionPath.length - 1];
    const node = findNode(tree, targetId);
    if (!node || !node.parentId) return null;
    const parent = findNode(tree, node.parentId);
    if (!parent) return null;
    return {
      wins: node.wins,
      visits: node.visits,
      parentVisits: parent.visits,
    };
  }, [tree, selectionPath, expandedNodeId]);

  /* ---------------------------------------------------------------- */
  /*  Phase badge config                                               */
  /* ---------------------------------------------------------------- */

  const phaseBadges: { key: MCTSPhase; label: string; color: string }[] = [
    { key: "selection", label: "Selection", color: "#22d3ee" },
    { key: "expansion", label: "Expansion", color: "#facc15" },
    { key: "simulation", label: "Simulation", color: "#a78bfa" },
    { key: "backpropagation", label: "Backprop", color: "#4ade80" },
  ];

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  const selectionPathSet = useMemo(() => new Set(selectionPath), [selectionPath]);
  const backpropSet = useMemo(() => new Set(backpropIds), [backpropIds]);

  return (
    <div className="widget-container s6">
      <div className="widget-label">Interactive &middot; Monte Carlo Tree Search</div>

      {/* Problem context */}
      <div
        style={{
          background: "rgba(250,204,21,0.06)",
          border: "1px solid rgba(250,204,21,0.15)",
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.8rem",
          color: "#e4e4e7",
          lineHeight: 1.6,
        }}
      >
        <span style={{ color: "#facc15", fontWeight: 600, marginRight: 6 }}>
          Goal:
        </span>
        Planning the best move in a strategy game
      </div>

      {/* Phase indicator badges */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        {phaseBadges.map((b) => {
          const isActive = phase === b.key;
          return (
            <span
              key={b.key}
              style={{
                fontFamily: "var(--font-mono), monospace",
                fontSize: "0.68rem",
                fontWeight: 600,
                letterSpacing: "0.04em",
                padding: "3px 10px",
                borderRadius: 6,
                border: `1px solid ${isActive ? b.color : "rgba(255,255,255,0.08)"}`,
                background: isActive
                  ? `${b.color}22`
                  : "rgba(255,255,255,0.03)",
                color: isActive ? b.color : "#52525b",
                transition: "all 0.3s",
              }}
            >
              {b.label}
            </span>
          );
        })}
      </div>

      {/* UCB1 Formula display */}
      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 8,
          padding: "0.6rem 1rem",
          marginBottom: "1rem",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.75rem",
          color: "#a1a1aa",
          lineHeight: 1.8,
          overflowX: "auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ color: "#e4e4e7", fontWeight: 600 }}>UCB1</span>
          <span style={{ color: "#52525b" }}>=</span>
          <span
            style={{
              color:
                selectedLeafForFormula && phase !== "idle"
                  ? "#22d3ee"
                  : "#a1a1aa",
              transition: "color 0.3s",
            }}
          >
            {selectedLeafForFormula && phase !== "idle"
              ? selectedLeafForFormula.wins
              : "w"}
          </span>
          <span style={{ color: "#52525b" }}>/</span>
          <span
            style={{
              color:
                selectedLeafForFormula && phase !== "idle"
                  ? "#22d3ee"
                  : "#a1a1aa",
              transition: "color 0.3s",
            }}
          >
            {selectedLeafForFormula && phase !== "idle"
              ? selectedLeafForFormula.visits
              : "n"}
          </span>
          <span style={{ color: "#52525b" }}>+</span>
          <span
            style={{
              color: "#facc15",
              fontWeight: 600,
            }}
          >
            {explorationC.toFixed(3)}
          </span>
          <span style={{ color: "#52525b" }}>*</span>
          <span style={{ color: "#a1a1aa" }}>
            sqrt( ln(
            <span
              style={{
                color:
                  selectedLeafForFormula && phase !== "idle"
                    ? "#4ade80"
                    : "#a1a1aa",
                transition: "color 0.3s",
              }}
            >
              {selectedLeafForFormula && phase !== "idle"
                ? selectedLeafForFormula.parentVisits
                : "N"}
            </span>
            ) /
            <span
              style={{
                color:
                  selectedLeafForFormula && phase !== "idle"
                    ? "#22d3ee"
                    : "#a1a1aa",
                transition: "color 0.3s",
              }}
            >
              {" "}
              {selectedLeafForFormula && phase !== "idle"
                ? selectedLeafForFormula.visits
                : "n"}
            </span>
            {" "})
          </span>
          {selectedLeafForFormula && phase !== "idle" && (
            <>
              <span style={{ color: "#52525b" }}>=</span>
              <span style={{ color: "#e4e4e7", fontWeight: 600 }}>
                {ucb1Display(
                  selectedLeafForFormula.wins,
                  selectedLeafForFormula.visits,
                  selectedLeafForFormula.parentVisits,
                  explorationC,
                )}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Controls row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn-mono"
          onClick={handleRunOne}
          disabled={phase !== "idle" || simCount >= maxSims}
          style={{
            opacity: phase !== "idle" || simCount >= maxSims ? 0.5 : 1,
            cursor:
              phase !== "idle" || simCount >= maxSims
                ? "not-allowed"
                : "pointer",
          }}
        >
          Run Simulation
        </button>

        <button
          className="btn-mono"
          onClick={handleRun5x}
          disabled={phase !== "idle" || simCount >= maxSims}
          style={{
            opacity: phase !== "idle" || simCount >= maxSims ? 0.5 : 1,
            cursor:
              phase !== "idle" || simCount >= maxSims
                ? "not-allowed"
                : "pointer",
          }}
        >
          Run 5x
        </button>

        <button
          className="btn-mono"
          onClick={handleReset}
          style={{
            opacity: phase !== "idle" ? 0.5 : 1,
            cursor: phase !== "idle" ? "not-allowed" : "pointer",
          }}
          disabled={phase !== "idle"}
        >
          Reset
        </button>

        {/* Simulation counter */}
        <span
          style={{
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.75rem",
            color: "#a1a1aa",
            marginLeft: "auto",
          }}
        >
          Simulations:{" "}
          <strong style={{ color: "#e4e4e7" }}>
            {simCount}/{maxSims}
          </strong>
        </span>
      </div>

      {/* C slider */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: "1rem",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.72rem",
          color: "#a1a1aa",
        }}
      >
        <span>Exploration C</span>
        <input
          type="range"
          min={0.5}
          max={2.0}
          step={0.01}
          value={explorationC}
          onChange={(e) => setExplorationC(Number(e.target.value))}
          disabled={phase !== "idle"}
          style={{ width: 120, accentColor: "#facc15" }}
        />
        <span style={{ color: "#facc15", fontWeight: 600, minWidth: 42 }}>
          {explorationC.toFixed(3)}
        </span>
      </div>

      {/* SVG Tree */}
      {mounted && (
        <div style={{ overflowX: "auto", marginBottom: "1rem" }}>
          <svg
            width={svgWidth}
            height={svgHeight}
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            style={{ display: "block", margin: "0 auto" }}
          >
            <defs>
              <style>{`
                @keyframes mctsNodePulse {
                  0% { opacity: 0; }
                  50% { opacity: 1; }
                  100% { opacity: 1; }
                }
                .mcts-new-node {
                  animation: mctsNodePulse 0.4s ease-out forwards;
                }
                @keyframes mctsFlash {
                  0% { opacity: 1; }
                  25% { opacity: 0.3; }
                  50% { opacity: 1; }
                  75% { opacity: 0.3; }
                  100% { opacity: 1; }
                }
                .mcts-flash {
                  animation: mctsFlash 0.5s ease-in-out;
                }
                @keyframes mctsGlow {
                  0% { filter: drop-shadow(0 0 0px #22d3ee); }
                  50% { filter: drop-shadow(0 0 8px #22d3ee); }
                  100% { filter: drop-shadow(0 0 4px #22d3ee); }
                }
                .mcts-selection-glow {
                  animation: mctsGlow 0.8s ease-in-out infinite;
                }
                @keyframes mctsYellowGlow {
                  0% { filter: drop-shadow(0 0 0px #facc15); }
                  50% { filter: drop-shadow(0 0 10px #facc15); }
                  100% { filter: drop-shadow(0 0 5px #facc15); }
                }
                .mcts-expand-glow {
                  animation: mctsYellowGlow 0.6s ease-in-out;
                }
                @keyframes rolloutDash {
                  from { stroke-dashoffset: 20; }
                  to { stroke-dashoffset: 0; }
                }
                .mcts-rollout-line {
                  animation: rolloutDash 0.5s linear infinite;
                }
              `}</style>

              {/* Glow filter for selection */}
              <filter id="cyanGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#22d3ee" floodOpacity="0.6" />
              </filter>
              <filter id="yellowGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#facc15" floodOpacity="0.7" />
              </filter>
              <filter id="greenGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#4ade80" floodOpacity="0.6" />
              </filter>
            </defs>

            {/* Edges */}
            {allNodes.map((node) => {
              if (!node.parentId) return null;
              const parentPos = posMap.get(node.parentId);
              const childPos = posMap.get(node.id);
              if (!parentPos || !childPos) return null;

              const isOnSelPath =
                selectionPathSet.has(node.id) &&
                selectionPathSet.has(node.parentId);

              const isBackprop =
                phase === "backpropagation" &&
                backpropSet.has(node.id) &&
                backpropSet.has(node.parentId);

              let strokeColor = "rgba(255,255,255,0.12)";
              let strokeW = 1;

              if (isBackprop) {
                strokeColor = "#4ade80";
                strokeW = 3;
              } else if (isOnSelPath && (phase === "selection" || phase === "expansion" || phase === "simulation")) {
                strokeColor = "#22d3ee";
                strokeW = 2.5;
              }

              return (
                <line
                  key={`edge-${node.id}`}
                  x1={parentPos.x}
                  y1={parentPos.y + 28}
                  x2={childPos.x}
                  y2={childPos.y - 28}
                  stroke={strokeColor}
                  strokeWidth={strokeW}
                  style={{ transition: "stroke 0.3s, stroke-width 0.3s" }}
                />
              );
            })}

            {/* Nodes */}
            {allNodes.map((node) => {
              const pos = posMap.get(node.id);
              if (!pos) return null;

              const isOnSelPath = selectionPathSet.has(node.id);
              const isExpanded = node.id === expandedNodeId;
              const isFlashing = flashingIds.has(node.id);
              const isBackprop = phase === "backpropagation" && backpropSet.has(node.id);

              // Determine node styling
              let fillColor = "rgba(255,255,255,0.04)";
              let strokeColor = "rgba(255,255,255,0.15)";
              let strokeW = 1;
              let filterAttr: string | undefined = undefined;
              let className = "";

              if (isFlashing) {
                fillColor = "rgba(74,222,128,0.15)";
                strokeColor = "#4ade80";
                strokeW = 2;
                filterAttr = "url(#greenGlow)";
                className = "mcts-flash";
              } else if (isExpanded && (phase === "expansion" || phase === "simulation")) {
                fillColor = "rgba(250,204,21,0.12)";
                strokeColor = "#facc15";
                strokeW = 2;
                filterAttr = "url(#yellowGlow)";
                className = "mcts-new-node";
              } else if (isOnSelPath && phase === "selection") {
                fillColor = "rgba(34,211,238,0.1)";
                strokeColor = "#22d3ee";
                strokeW = 2;
                filterAttr = "url(#cyanGlow)";
              } else if (isOnSelPath && (phase === "expansion" || phase === "simulation" || phase === "backpropagation")) {
                fillColor = "rgba(34,211,238,0.06)";
                strokeColor = "#22d3ee";
                strokeW = 1.5;
              }

              // Parent for UCB1 display
              let parentNode: MCTSNode | null = null;
              if (node.parentId) {
                parentNode = findNode(tree, node.parentId);
              }

              const nodeR = 26;

              return (
                <g
                  key={`node-${node.id}`}
                  className={className}
                  style={{ transition: "opacity 0.3s" }}
                >
                  {/* Node circle */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={nodeR}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={strokeW}
                    filter={filterAttr}
                    style={{ transition: "fill 0.3s, stroke 0.3s" }}
                  />

                  {/* Label above */}
                  <text
                    x={pos.x}
                    y={pos.y - nodeR - 6}
                    textAnchor="middle"
                    fill="#a1a1aa"
                    fontFamily="var(--font-mono), monospace"
                    fontSize={9}
                    style={{ pointerEvents: "none" }}
                  >
                    {node.label}
                  </text>

                  {/* Wins/Visits inside */}
                  <text
                    x={pos.x}
                    y={pos.y + 1}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="#e4e4e7"
                    fontFamily="var(--font-mono), monospace"
                    fontSize={11}
                    fontWeight={600}
                    style={{ pointerEvents: "none" }}
                  >
                    {node.visits === 0 ? "0/0" : `${node.wins}/${node.visits}`}
                  </text>

                  {/* UCB1 score below node */}
                  {parentNode && node.visits > 0 && (
                    <text
                      x={pos.x}
                      y={pos.y + nodeR + 14}
                      textAnchor="middle"
                      fill={
                        isOnSelPath &&
                        (phase === "selection" || phase === "expansion")
                          ? "#22d3ee"
                          : "#52525b"
                      }
                      fontFamily="var(--font-mono), monospace"
                      fontSize={8.5}
                      style={{
                        pointerEvents: "none",
                        transition: "fill 0.3s",
                      }}
                    >
                      UCB1:{" "}
                      {ucb1Display(
                        node.wins,
                        node.visits,
                        parentNode.visits,
                        explorationC,
                      )}
                    </text>
                  )}

                  {/* New node: 0/0 with yellow indicator */}
                  {isExpanded && node.visits === 0 && (
                    <text
                      x={pos.x}
                      y={pos.y + nodeR + 14}
                      textAnchor="middle"
                      fill="#facc15"
                      fontFamily="var(--font-mono), monospace"
                      fontSize={8.5}
                      fontWeight={600}
                      style={{ pointerEvents: "none" }}
                    >
                      new
                    </text>
                  )}
                </g>
              );
            })}

            {/* Rollout line during simulation */}
            {phase === "simulation" && expandedNodeId && (() => {
              const expandedPos = posMap.get(expandedNodeId);
              if (!expandedPos) return null;

              const rolloutEndY = expandedPos.y + 70;

              return (
                <g>
                  {/* Dotted rollout line */}
                  <line
                    x1={expandedPos.x}
                    y1={expandedPos.y + 28}
                    x2={expandedPos.x}
                    y2={rolloutEndY}
                    stroke="#a78bfa"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    className="mcts-rollout-line"
                  />

                  {/* Rollout result badge */}
                  {rolloutResult !== null && (
                    <g>
                      <rect
                        x={expandedPos.x - 24}
                        y={rolloutEndY + 4}
                        width={48}
                        height={20}
                        rx={6}
                        fill={
                          rolloutResult
                            ? "rgba(74,222,128,0.15)"
                            : "rgba(248,113,113,0.15)"
                        }
                        stroke={rolloutResult ? "#4ade80" : "#f87171"}
                        strokeWidth={1}
                      />
                      <text
                        x={expandedPos.x}
                        y={rolloutEndY + 17}
                        textAnchor="middle"
                        fill={rolloutResult ? "#4ade80" : "#f87171"}
                        fontFamily="var(--font-mono), monospace"
                        fontSize={10}
                        fontWeight={700}
                      >
                        {rolloutResult ? "Win" : "Loss"}
                      </text>
                    </g>
                  )}

                  {/* Rollout label */}
                  <text
                    x={expandedPos.x + 30}
                    y={expandedPos.y + 55}
                    fill="#a78bfa"
                    fontFamily="var(--font-mono), monospace"
                    fontSize={8.5}
                    style={{ pointerEvents: "none" }}
                  >
                    random rollout
                  </text>
                </g>
              );
            })()}
          </svg>
        </div>
      )}

      {/* Status bar */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.72rem",
          color: "#a1a1aa",
          marginBottom: "0.5rem",
          minHeight: 20,
        }}
      >
        {phase === "idle" && simCount === 0 && (
          <span>
            Press{" "}
            <strong style={{ color: "#e4e4e7" }}>Run Simulation</strong> to
            begin MCTS cycle
          </span>
        )}
        {phase === "idle" && simCount > 0 && simCount < maxSims && (
          <span>
            Cycle complete. Run more simulations to improve the search tree.
          </span>
        )}
        {phase === "idle" && simCount >= maxSims && (
          <span style={{ color: "#4ade80" }}>
            All {maxSims} simulations complete. Tree is fully explored.
          </span>
        )}
        {phase === "selection" && (
          <span>
            <strong style={{ color: "#22d3ee" }}>Selection:</strong> Traversing
            tree via UCB1 to find most promising leaf...
          </span>
        )}
        {phase === "expansion" && (
          <span>
            <strong style={{ color: "#facc15" }}>Expansion:</strong> Adding new
            child node at the selected leaf...
          </span>
        )}
        {phase === "simulation" && (
          <span>
            <strong style={{ color: "#a78bfa" }}>Simulation:</strong> Running
            random rollout from expanded node...{" "}
            {rolloutResult !== null && (
              <span
                style={{
                  color: rolloutResult ? "#4ade80" : "#f87171",
                  fontWeight: 600,
                }}
              >
                {rolloutResult ? "Win!" : "Loss."}
              </span>
            )}
          </span>
        )}
        {phase === "backpropagation" && (
          <span>
            <strong style={{ color: "#4ade80" }}>Backpropagation:</strong>{" "}
            Updating win/visit counts along the selected path...
          </span>
        )}
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          marginTop: "0.5rem",
          flexWrap: "wrap",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.68rem",
          color: "#a1a1aa",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 16,
              height: 2,
              background: "#22d3ee",
              display: "inline-block",
              borderRadius: 1,
            }}
          />
          selection path
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "rgba(250,204,21,0.3)",
              border: "1px solid #facc15",
              display: "inline-block",
            }}
          />
          expanded
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 16,
              height: 2,
              background: "#a78bfa",
              display: "inline-block",
              borderRadius: 1,
              borderBottom: "1px dashed #a78bfa",
            }}
          />
          rollout
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 16,
              height: 2,
              background: "#4ade80",
              display: "inline-block",
              borderRadius: 1,
            }}
          />
          backprop
        </span>
      </div>
    </div>
  );
}
