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

interface TreeNode {
  id: string;
  label: string;
  score: number | null;
  depth: number;
  children: TreeNode[];
  pruned: boolean;
  onBestPath: boolean;
}

type Phase = "idle" | "exploring" | "done";

/* ------------------------------------------------------------------ */
/*  Hardcoded thought bank (deterministic)                             */
/* ------------------------------------------------------------------ */

const THOUGHT_BANK: {
  label: string;
  score: number;
}[][] = [
  /* depth-0 (root) is handled separately */
  /* depth-1 candidates */
  [
    { label: "Start with center=5", score: 0.8 },
    { label: "Start with center=1", score: 0.3 },
    { label: "Start with corners", score: 0.6 },
    { label: "Start with edges", score: 0.25 },
  ],
  /* depth-2 candidates from best depth-1 */
  [
    { label: "Row1: 2,7,6", score: 0.9 },
    { label: "Row1: 4,3,8", score: 0.7 },
    { label: "Row1: 8,1,6", score: 0.75 },
    { label: "Row1: 6,7,2", score: 0.85 },
  ],
  /* depth-2 candidates from worse depth-1 */
  [
    { label: "Row1: 9,5,1", score: 0.2 },
    { label: "Row1: 8,3,4", score: 0.4 },
    { label: "Row1: 7,2,6", score: 0.35 },
    { label: "Row1: 3,8,4", score: 0.15 },
  ],
  /* depth-3 candidates from best depth-2 */
  [
    { label: "Row2: 9,5,1", score: 0.95 },
    { label: "Row2: 4,5,6", score: 0.82 },
    { label: "Row2: 3,5,7", score: 0.88 },
    { label: "Row2: 6,5,4", score: 0.78 },
  ],
  /* depth-3 candidates from second-best depth-2 */
  [
    { label: "Row2: 9,5,1", score: 0.6 },
    { label: "Row2: 2,5,8", score: 0.55 },
    { label: "Row2: 6,5,4", score: 0.5 },
    { label: "Row2: 1,5,9", score: 0.65 },
  ],
];

/* ------------------------------------------------------------------ */
/*  Build tree                                                         */
/* ------------------------------------------------------------------ */

function buildTree(width: number, depth: number): TreeNode {
  let nextId = 0;

  const root: TreeNode = {
    id: `n${nextId++}`,
    label: "How to arrange numbers?",
    score: null,
    depth: 0,
    children: [],
    pruned: false,
    onBestPath: true,
  };

  function addChildren(
    parent: TreeNode,
    currentDepth: number,
    bankIndex: number,
  ) {
    if (currentDepth >= depth) return;

    const bank = THOUGHT_BANK[bankIndex] ?? THOUGHT_BANK[0];
    const count = Math.min(width, bank.length);

    const candidates = bank.slice(0, count).map((t) => ({
      ...t,
    }));
    /* sort descending by score for deterministic pruning */
    candidates.sort((a, b) => b.score - a.score);

    for (let i = 0; i < candidates.length; i++) {
      const node: TreeNode = {
        id: `n${nextId++}`,
        label: candidates[i].label,
        score: candidates[i].score,
        depth: currentDepth + 1,
        children: [],
        pruned: i >= width, /* prune beyond width (already sorted) */
        onBestPath: false,
      };
      parent.children.push(node);
    }
  }

  /* depth-1 */
  addChildren(root, 0, 0);

  /* depth-2+ : attach children to the top-width nodes of each parent */
  function expandLevel(nodes: TreeNode[], depthNow: number, bankStart: number) {
    if (depthNow >= depth) return;
    let bankIdx = bankStart;
    for (const node of nodes) {
      if (node.pruned) continue;
      addChildren(node, depthNow, bankIdx);
      bankIdx++;
      expandLevel(
        node.children,
        depthNow + 1,
        bankIdx,
      );
    }
  }

  expandLevel(root.children, 1, 1);

  /* Mark best path (greedy highest score at each level) */
  function markBest(node: TreeNode) {
    node.onBestPath = true;
    if (node.children.length === 0) return;
    const nonPruned = node.children.filter((c) => !c.pruned);
    if (nonPruned.length === 0) return;
    const best = nonPruned.reduce((a, b) =>
      (b.score ?? 0) > (a.score ?? 0) ? b : a,
    );
    markBest(best);
  }
  markBest(root);

  return root;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColor(score: number | null): string {
  if (score === null) return "#a1a1aa";
  if (score > 0.7) return "#4ade80";
  if (score >= 0.4) return "#facc15";
  return "#f87171";
}

function scoreColorBg(score: number | null): string {
  if (score === null) return "rgba(161,161,170,0.15)";
  if (score > 0.7) return "rgba(74,222,128,0.15)";
  if (score >= 0.4) return "rgba(250,204,21,0.15)";
  return "rgba(248,113,113,0.15)";
}

/** Flatten tree into a list of nodes per depth level */
function flattenByDepth(root: TreeNode): TreeNode[][] {
  const levels: TreeNode[][] = [];
  const queue: TreeNode[] = [root];
  while (queue.length > 0) {
    const size = queue.length;
    const level: TreeNode[] = [];
    for (let i = 0; i < size; i++) {
      const node = queue.shift()!;
      level.push(node);
      for (const child of node.children) {
        queue.push(child);
      }
    }
    levels.push(level);
  }
  return levels;
}

/** Compute positioned layout */
interface PositionedNode {
  node: TreeNode;
  x: number;
  y: number;
  parentId: string | null;
}

function layoutTree(
  root: TreeNode,
  svgWidth: number,
  svgHeight: number,
): PositionedNode[] {
  const levels = flattenByDepth(root);
  const totalDepth = levels.length;
  const yPad = 60;
  const yStep = totalDepth > 1 ? (svgHeight - yPad * 2) / (totalDepth - 1) : 0;

  const result: PositionedNode[] = [];

  /* Build parent map */
  const parentMap = new Map<string, string>();
  function mapParents(n: TreeNode) {
    for (const c of n.children) {
      parentMap.set(c.id, n.id);
      mapParents(c);
    }
  }
  mapParents(root);

  for (let d = 0; d < levels.length; d++) {
    const level = levels[d];
    const count = level.length;
    const xPad = 50;
    const usable = svgWidth - xPad * 2;
    const xStep = count > 1 ? usable / (count - 1) : 0;

    for (let i = 0; i < count; i++) {
      result.push({
        node: level[i],
        x: count > 1 ? xPad + i * xStep : svgWidth / 2,
        y: yPad + d * yStep,
        parentId: parentMap.get(level[i].id) ?? null,
      });
    }
  }

  return result;
}

/* ------------------------------------------------------------------ */
/*  Synthesis text for best path                                       */
/* ------------------------------------------------------------------ */

function getBestPathLabels(root: TreeNode): string[] {
  const path: string[] = [];
  function walk(node: TreeNode) {
    path.push(node.label);
    const nonPruned = node.children.filter((c) => !c.pruned && c.onBestPath);
    if (nonPruned.length > 0) walk(nonPruned[0]);
  }
  walk(root);
  return path;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ToTTreeWidget() {
  /* Hydration guard */
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  /* Config */
  const [width, setWidth] = useState(2);
  const [depth, setDepth] = useState(3);

  /* Animation state */
  const [phase, setPhase] = useState<Phase>("idle");
  const [revealedDepth, setRevealedDepth] = useState(0);
  const [scoringDepth, setScoringDepth] = useState(-1);
  const [pruningDepth, setPruningDepth] = useState(-1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Tree data */
  const tree = useMemo(() => buildTree(width, depth), [width, depth]);
  const levels = useMemo(() => flattenByDepth(tree), [tree]);

  /* SVG dimensions */
  const svgWidth = 560;
  const svgHeight = Math.max(260, levels.length * 120 + 40);
  const positioned = useMemo(
    () => layoutTree(tree, svgWidth, svgHeight),
    [tree, svgWidth, svgHeight],
  );

  /* Position lookup */
  const posMap = useMemo(() => {
    const m = new Map<string, PositionedNode>();
    for (const p of positioned) m.set(p.node.id, p);
    return m;
  }, [positioned]);

  /* Best path labels */
  const bestPath = useMemo(() => getBestPathLabels(tree), [tree]);

  /* Reset when config changes */
  useEffect(() => {
    setPhase("idle");
    setRevealedDepth(0);
    setScoringDepth(-1);
    setPruningDepth(-1);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, [width, depth]);

  /* Explore animation */
  const explore = useCallback(() => {
    if (phase === "exploring") return;
    setPhase("exploring");
    setRevealedDepth(0);
    setScoringDepth(-1);
    setPruningDepth(-1);

    const totalLevels = levels.length;
    let currentLevel = 0;

    function stepReveal() {
      currentLevel++;
      if (currentLevel >= totalLevels) {
        setPhase("done");
        return;
      }
      /* Show candidates */
      setRevealedDepth(currentLevel);
      setScoringDepth(-1);
      setPruningDepth(-1);

      /* After a beat, show scores */
      timerRef.current = setTimeout(() => {
        setScoringDepth(currentLevel);

        /* After another beat, prune */
        timerRef.current = setTimeout(() => {
          setPruningDepth(currentLevel);

          /* Move to next level */
          timerRef.current = setTimeout(stepReveal, 600);
        }, 600);
      }, 600);
    }

    stepReveal();
  }, [phase, levels.length]);

  /* Cleanup */
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  /* Node visibility logic */
  const isNodeVisible = useCallback(
    (node: TreeNode): boolean => {
      if (phase === "idle") return node.depth === 0;
      if (phase === "done") return true;
      /* exploring */
      return node.depth <= revealedDepth;
    },
    [phase, revealedDepth],
  );

  const isScoreVisible = useCallback(
    (node: TreeNode): boolean => {
      if (node.score === null) return false;
      if (phase === "done") return true;
      if (phase === "idle") return false;
      return node.depth <= scoringDepth;
    },
    [phase, scoringDepth],
  );

  const isPruningVisible = useCallback(
    (node: TreeNode): boolean => {
      if (phase === "done") return true;
      if (phase === "idle") return false;
      return node.depth <= pruningDepth;
    },
    [phase, pruningDepth],
  );

  const showBestPath = phase === "done";

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="widget-container s2">
      <div className="widget-label">Interactive &middot; Tree of Thoughts (BFS)</div>

      {/* Problem statement */}
      <div
        style={{
          background: "rgba(34,211,238,0.06)",
          border: "1px solid rgba(34,211,238,0.15)",
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.8rem",
          color: "#e4e4e7",
          lineHeight: 1.6,
        }}
      >
        <span style={{ color: "#22d3ee", fontWeight: 600, marginRight: 6 }}>
          Puzzle:
        </span>
        Arrange the numbers 1&ndash;9 in a 3&times;3 grid so each row, column,
        and diagonal sums to 15
      </div>

      {/* Controls row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1.25rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <button
          className="btn-mono"
          onClick={explore}
          disabled={phase === "exploring"}
          style={{
            opacity: phase === "exploring" ? 0.5 : 1,
            cursor: phase === "exploring" ? "not-allowed" : "pointer",
          }}
        >
          {phase === "idle"
            ? "Explore"
            : phase === "exploring"
              ? "Exploring..."
              : "Re-Explore"}
        </button>

        {/* Width slider */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.72rem",
            color: "#a1a1aa",
          }}
        >
          Width
          <input
            type="range"
            min={1}
            max={4}
            value={width}
            onChange={(e) => setWidth(Number(e.target.value))}
            style={{ width: 80 }}
          />
          <span style={{ color: "#e4e4e7", minWidth: 14, textAlign: "center" }}>
            {width}
          </span>
        </label>

        {/* Depth slider */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: "var(--font-mono), monospace",
            fontSize: "0.72rem",
            color: "#a1a1aa",
          }}
        >
          Depth
          <input
            type="range"
            min={1}
            max={4}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            style={{ width: 80 }}
          />
          <span style={{ color: "#e4e4e7", minWidth: 14, textAlign: "center" }}>
            {depth}
          </span>
        </label>
      </div>

      {/* SVG Tree */}
      {mounted && (
        <div
          style={{
            overflowX: "auto",
            marginBottom: "1rem",
          }}
        >
          <svg
            width={svgWidth}
            height={svgHeight}
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            style={{ display: "block", margin: "0 auto" }}
          >
            <defs>
              {/* Node pulse animation */}
              <style>{`
                @keyframes nodePulse {
                  0% { r: 24; opacity: 0; }
                  30% { r: 30; opacity: 1; }
                  100% { r: 24; opacity: 1; }
                }
                .node-appear {
                  animation: nodePulse 0.5s ease-out forwards;
                }
                @keyframes scoreSlideIn {
                  from { opacity: 0; transform: translateY(4px); }
                  to { opacity: 1; transform: translateY(0); }
                }
                .score-appear {
                  animation: scoreSlideIn 0.3s ease-out forwards;
                }
                @keyframes edgeGlow {
                  0% { stroke-opacity: 0.3; }
                  50% { stroke-opacity: 1; }
                  100% { stroke-opacity: 0.8; }
                }
                .best-edge {
                  animation: edgeGlow 0.8s ease-out forwards;
                }
              `}</style>
            </defs>

            {/* Edges */}
            {positioned.map((pn) => {
              if (!pn.parentId) return null;
              const parent = posMap.get(pn.parentId);
              if (!parent) return null;
              if (!isNodeVisible(pn.node)) return null;
              if (!isNodeVisible(parent.node)) return null;

              const isBest =
                showBestPath && pn.node.onBestPath && parent.node.onBestPath;
              const dimmed =
                isPruningVisible(pn.node) && pn.node.pruned;

              return (
                <line
                  key={`edge-${pn.node.id}`}
                  x1={parent.x}
                  y1={parent.y + 24}
                  x2={pn.x}
                  y2={pn.y - 24}
                  stroke={isBest ? "#22d3ee" : "rgba(255,255,255,0.2)"}
                  strokeWidth={isBest ? 2.5 : 1}
                  opacity={dimmed ? 0.15 : 1}
                  className={isBest ? "best-edge" : undefined}
                />
              );
            })}

            {/* Nodes */}
            {positioned.map((pn) => {
              if (!isNodeVisible(pn.node)) return null;

              const node = pn.node;
              const showScore = isScoreVisible(node);
              const dimmed = isPruningVisible(node) && node.pruned;
              const isBest = showBestPath && node.onBestPath;
              const fillColor = showScore
                ? scoreColorBg(node.score)
                : "rgba(255,255,255,0.05)";
              const strokeColor = isBest
                ? "#22d3ee"
                : showScore
                  ? scoreColor(node.score)
                  : "rgba(255,255,255,0.15)";

              /* Label truncation for small circles */
              const shortLabel =
                node.label.length > 18
                  ? node.label.slice(0, 16) + "..."
                  : node.label;

              return (
                <g
                  key={`node-${node.id}`}
                  opacity={dimmed ? 0.3 : 1}
                  style={{ transition: "opacity 0.4s" }}
                >
                  {/* Circle */}
                  <circle
                    cx={pn.x}
                    cy={pn.y}
                    r={24}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={isBest ? 2 : 1}
                    className="node-appear"
                  />

                  {/* Pruned strikethrough */}
                  {dimmed && (
                    <line
                      x1={pn.x - 18}
                      y1={pn.y}
                      x2={pn.x + 18}
                      y2={pn.y}
                      stroke="#f87171"
                      strokeWidth={1.5}
                      opacity={0.7}
                    />
                  )}

                  {/* Label above circle */}
                  <text
                    x={pn.x}
                    y={pn.y - 30}
                    textAnchor="middle"
                    fill={dimmed ? "#52525b" : "#e4e4e7"}
                    fontFamily="var(--font-mono), monospace"
                    fontSize={10}
                    style={{ pointerEvents: "none" }}
                  >
                    {shortLabel}
                  </text>

                  {/* Score inside circle */}
                  {node.score !== null && (
                    <text
                      x={pn.x}
                      y={pn.y + 4}
                      textAnchor="middle"
                      fill={showScore ? scoreColor(node.score) : "transparent"}
                      fontFamily="var(--font-mono), monospace"
                      fontSize={11}
                      fontWeight={600}
                      style={{
                        transition: "fill 0.3s",
                        pointerEvents: "none",
                      }}
                    >
                      {node.score.toFixed(1)}
                    </text>
                  )}

                  {/* Root label (no score) */}
                  {node.score === null && (
                    <text
                      x={pn.x}
                      y={pn.y + 3}
                      textAnchor="middle"
                      fill="#a1a1aa"
                      fontFamily="var(--font-mono), monospace"
                      fontSize={9}
                      style={{ pointerEvents: "none" }}
                    >
                      root
                    </text>
                  )}

                  {/* Score badge below circle */}
                  {showScore && node.score !== null && (
                    <g className="score-appear">
                      <rect
                        x={pn.x - 18}
                        y={pn.y + 28}
                        width={36}
                        height={18}
                        rx={4}
                        fill={scoreColorBg(node.score)}
                        stroke={scoreColor(node.score)}
                        strokeWidth={0.5}
                        opacity={0.9}
                      />
                      <text
                        x={pn.x}
                        y={pn.y + 40}
                        textAnchor="middle"
                        fill={scoreColor(node.score)}
                        fontFamily="var(--font-mono), monospace"
                        fontSize={9}
                        fontWeight={600}
                      >
                        {node.score.toFixed(2)}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      )}

      {/* Status bar */}
      <div
        style={{
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.72rem",
          color: "#a1a1aa",
          marginBottom: phase === "done" ? "0.75rem" : 0,
          minHeight: 20,
        }}
      >
        {phase === "idle" && (
          <span>
            Press <strong style={{ color: "#e4e4e7" }}>Explore</strong> to begin
            BFS tree search
          </span>
        )}
        {phase === "exploring" && revealedDepth > 0 && (
          <span>
            {scoringDepth >= revealedDepth
              ? pruningDepth >= revealedDepth
                ? `Level ${revealedDepth}: pruned low-scoring branches`
                : `Level ${revealedDepth}: scoring candidates...`
              : `Level ${revealedDepth}: generating candidate thoughts...`}
          </span>
        )}
        {phase === "done" && (
          <span style={{ color: "#4ade80" }}>
            Search complete &mdash; best path highlighted in cyan
          </span>
        )}
      </div>

      {/* Synthesis */}
      {phase === "done" && (
        <div
          style={{
            background: "rgba(34,211,238,0.05)",
            border: "1px solid rgba(34,211,238,0.12)",
            borderRadius: 8,
            padding: "0.75rem 1rem",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.7rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#22d3ee",
              marginBottom: "0.5rem",
              fontWeight: 600,
            }}
          >
            Synthesis &mdash; Best Path
          </div>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "0.4rem",
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.78rem",
              color: "#e4e4e7",
              lineHeight: 1.8,
            }}
          >
            {bestPath.map((label, i) => (
              <span key={i} style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span
                  style={{
                    background: "rgba(34,211,238,0.12)",
                    border: "1px solid rgba(34,211,238,0.2)",
                    borderRadius: 4,
                    padding: "2px 8px",
                  }}
                >
                  {label}
                </span>
                {i < bestPath.length - 1 && (
                  <span style={{ color: "#52525b" }}>&rarr;</span>
                )}
              </span>
            ))}
          </div>
          <div
            style={{
              fontFamily: "var(--font-mono), monospace",
              fontSize: "0.72rem",
              color: "#a1a1aa",
              marginTop: "0.5rem",
              lineHeight: 1.6,
            }}
          >
            The BFS exploration evaluated{" "}
            <strong style={{ color: "#e4e4e7" }}>
              {positioned.length}
            </strong>{" "}
            candidate thoughts across{" "}
            <strong style={{ color: "#e4e4e7" }}>{levels.length - 1}</strong>{" "}
            depth levels, pruning low-scoring branches at each step to arrive at
            the optimal solution path.
          </div>
        </div>
      )}

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          marginTop: "0.75rem",
          flexWrap: "wrap",
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.68rem",
          color: "#a1a1aa",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#4ade80",
              display: "inline-block",
            }}
          />
          &gt;0.7
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#facc15",
              display: "inline-block",
            }}
          />
          0.4&ndash;0.7
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#f87171",
              display: "inline-block",
            }}
          />
          &lt;0.4
        </span>
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
          best path
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              display: "inline-block",
              opacity: 0.3,
            }}
          />
          pruned
        </span>
      </div>
    </div>
  );
}
