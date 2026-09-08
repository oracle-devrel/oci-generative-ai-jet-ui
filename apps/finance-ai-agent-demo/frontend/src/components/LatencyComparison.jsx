import { useState } from "react";

/**
 * Latency comparison tab — SVG line graph showing converged vs sprawl latency
 * per tool call, with dots at each query point. Only visible in comparison mode.
 */
export default function LatencyComparison({ comparisonData, healthStatus, onHealthCheck }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const points = comparisonData?.latency_points || [];
  const hasData = points.length > 0;

  // Graph dimensions
  const W = 460;
  const H = 220;
  const PAD_L = 50;
  const PAD_R = 20;
  const PAD_T = 30;
  const PAD_B = 60;
  const graphW = W - PAD_L - PAD_R;
  const graphH = H - PAD_T - PAD_B;

  // Scale
  const maxMs = hasData
    ? Math.max(...points.map((p) => Math.max(p.converged_ms || 0, p.sprawl_ms || 0)), 10) * 1.15
    : 100;
  const xStep = hasData ? graphW / Math.max(points.length - 1, 1) : graphW;

  const toX = (i) => PAD_L + i * xStep;
  const toY = (ms) => PAD_T + graphH - (ms / maxMs) * graphH;

  // Build paths
  const convergedPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(p.converged_ms || 0)}`)
    .join(" ");
  const sprawlPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(p.sprawl_ms || 0)}`)
    .join(" ");

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    ms: Math.round(maxMs * f),
    y: toY(maxMs * f),
  }));

  // Health status colors
  const statusColor = (s) => {
    if (!s) return "bg-gray-600";
    if (s.status === "connected") return "bg-green-500";
    if (s.status === "error") return "bg-red-500";
    return "bg-gray-600";
  };

  const statusLabel = (s) => {
    if (!s) return "Unknown";
    if (s.status === "connected") return `${s.latency_ms}ms`;
    if (s.status === "error") return s.error?.substring(0, 40) || "Error";
    return "Not configured";
  };

  const dbList = [
    { key: "oracle", label: "Oracle AI Database", color: "#DC2626" },
    { key: "postgresql", label: "PostgreSQL", color: "#2563EB" },
    { key: "neo4j", label: "Neo4j", color: "#059669" },
    { key: "mongodb", label: "MongoDB", color: "#D97706" },
    { key: "qdrant", label: "Qdrant", color: "#7C3AED" },
  ];

  return (
    <div className="h-full overflow-y-auto p-3 space-y-4 text-xs">
      {/* Health Check Panel */}
      <div className="bg-primary/40 rounded-lg border border-white/5 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-text-secondary font-medium text-[11px] uppercase tracking-wider">
            Database Health
          </span>
          <button
            onClick={onHealthCheck}
            className="text-[10px] text-text-accent hover:text-blue-300 transition"
          >
            Refresh
          </button>
        </div>
        <div className="space-y-1.5">
          {dbList.map((db) => {
            const s = healthStatus?.[db.key];
            return (
              <div key={db.key} className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${statusColor(s)}`}
                  style={s?.status === "error" ? { animation: "pulse 1.5s infinite" } : undefined}
                />
                <span className="text-text-secondary w-20 truncate" style={{ color: db.color }}>
                  {db.label}
                </span>
                <span
                  className={`text-[10px] ml-auto ${s?.status === "error" ? "text-red-400" : "text-text-secondary/60"}`}
                >
                  {statusLabel(s)}
                </span>
              </div>
            );
          })}
        </div>
        {/* Connection count indicator */}
        {healthStatus && (
          <div className="mt-2 pt-2 border-t border-white/5 flex gap-3 text-[10px] text-text-secondary/50">
            <span>
              {Object.values(healthStatus).filter((s) => s?.status === "connected").length}{" "}
              connected
            </span>
            <span className="text-red-400/70">
              {Object.values(healthStatus).filter((s) => s?.status === "error").length} failed
            </span>
            <span>
              {Object.values(healthStatus).filter((s) => s?.status === "connected").length} failure
              domains
            </span>
          </div>
        )}
      </div>

      {/* Latency Graph */}
      <div className="bg-primary/40 rounded-lg border border-white/5 p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-text-secondary font-medium text-[11px] uppercase tracking-wider">
            Tool Call Latency
          </span>
          {comparisonData && (
            <span className="text-[10px] text-text-secondary/50">
              {comparisonData.tool_count} tools benchmarked
            </span>
          )}
        </div>

        {!hasData ? (
          <div className="flex items-center justify-center h-40 text-text-secondary/40 text-[11px]">
            Send a message in comparison mode to see latency data
          </div>
        ) : (
          <>
            <svg width={W} height={H} className="w-full" viewBox={`0 0 ${W} ${H}`}>
              {/* Grid lines */}
              {yTicks.map((t, i) => (
                <g key={i}>
                  <line
                    x1={PAD_L}
                    y1={t.y}
                    x2={W - PAD_R}
                    y2={t.y}
                    stroke="rgba(255,255,255,0.05)"
                  />
                  <text
                    x={PAD_L - 6}
                    y={t.y + 3}
                    textAnchor="end"
                    fill="rgba(255,255,255,0.3)"
                    fontSize="9"
                  >
                    {t.ms}ms
                  </text>
                </g>
              ))}

              {/* Converged line (blue) */}
              <path
                d={convergedPath}
                fill="none"
                stroke="#3B82F6"
                strokeWidth="2"
                strokeLinecap="round"
              />
              {/* Sprawl line (amber) */}
              <path
                d={sprawlPath}
                fill="none"
                stroke="#F59E0B"
                strokeWidth="2"
                strokeLinecap="round"
                strokeDasharray={hasData && points.some((p) => p.sprawl_error) ? "4,3" : "none"}
              />

              {/* Data points - converged */}
              {points.map((p, i) => (
                <g key={`c-${i}`}>
                  <circle
                    cx={toX(i)}
                    cy={toY(p.converged_ms || 0)}
                    r={hoveredPoint === i ? 5 : 3.5}
                    fill={p.converged_error ? "#EF4444" : "#3B82F6"}
                    stroke="#1e1e2e"
                    strokeWidth="1.5"
                    className="cursor-pointer transition-all"
                    onMouseEnter={() => setHoveredPoint(i)}
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                  {p.converged_error && (
                    <text
                      x={toX(i)}
                      y={toY(p.converged_ms || 0) - 8}
                      textAnchor="middle"
                      fill="#EF4444"
                      fontSize="8"
                    >
                      ERR
                    </text>
                  )}
                </g>
              ))}

              {/* Data points - sprawl */}
              {points.map((p, i) => (
                <g key={`s-${i}`}>
                  <circle
                    cx={toX(i)}
                    cy={toY(p.sprawl_ms || 0)}
                    r={hoveredPoint === i ? 5 : 3.5}
                    fill={p.sprawl_error ? "#EF4444" : "#F59E0B"}
                    stroke="#1e1e2e"
                    strokeWidth="1.5"
                    className="cursor-pointer transition-all"
                    onMouseEnter={() => setHoveredPoint(i)}
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                  {p.sprawl_error && (
                    <text
                      x={toX(i)}
                      y={toY(p.sprawl_ms || 0) + 14}
                      textAnchor="middle"
                      fill="#EF4444"
                      fontSize="8"
                    >
                      ERR
                    </text>
                  )}
                </g>
              ))}

              {/* X-axis labels */}
              {points.map((p, i) => (
                <text
                  key={`xl-${i}`}
                  x={toX(i)}
                  y={H - PAD_B + 16}
                  textAnchor="middle"
                  fill="rgba(255,255,255,0.35)"
                  fontSize="8"
                  transform={`rotate(-30, ${toX(i)}, ${H - PAD_B + 16})`}
                >
                  {p.tool?.replace(/_/g, " ").substring(0, 16)}
                </text>
              ))}
            </svg>

            {/* Tooltip */}
            {hoveredPoint !== null && points[hoveredPoint] && (
              <div className="mt-1 p-2 bg-black/60 rounded text-[10px] space-y-0.5 border border-white/10">
                <div className="font-medium text-text-primary">{points[hoveredPoint].tool}</div>
                <div className="flex gap-4">
                  <span className="text-blue-400">
                    Converged: {points[hoveredPoint].converged_ms}ms
                    {points[hoveredPoint].converged_error && (
                      <span className="text-red-400 ml-1">FAILED</span>
                    )}
                  </span>
                  <span className="text-amber-400">
                    Sprawl: {points[hoveredPoint].sprawl_ms}ms
                    {points[hoveredPoint].sprawl_error && (
                      <span className="text-red-400 ml-1">FAILED</span>
                    )}
                  </span>
                </div>
              </div>
            )}

            {/* Legend */}
            <div className="flex items-center gap-4 mt-2 text-[10px]">
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-blue-500 inline-block rounded" />
                <span className="text-blue-400">Converged (1 query)</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-amber-500 inline-block rounded" />
                <span className="text-amber-400">Sprawl (sequential)</span>
              </span>
            </div>
          </>
        )}
      </div>

      {/* Summary stats */}
      {comparisonData && hasData && (
        <div className="bg-primary/40 rounded-lg border border-white/5 p-3 space-y-2">
          <span className="text-text-secondary font-medium text-[11px] uppercase tracking-wider">
            Cumulative Latency
          </span>
          <div className="grid grid-cols-2 gap-3 mt-1">
            <div className="text-center p-2 bg-blue-500/10 rounded border border-blue-500/20">
              <div className="text-lg font-bold text-blue-400">
                {comparisonData.total_converged_ms}ms
              </div>
              <div className="text-[10px] text-text-secondary/50">Converged (Oracle)</div>
              {comparisonData.converged_errors > 0 && (
                <div className="text-[10px] text-red-400 mt-0.5">
                  {comparisonData.converged_errors} error
                  {comparisonData.converged_errors > 1 ? "s" : ""}
                </div>
              )}
            </div>
            <div className="text-center p-2 bg-amber-500/10 rounded border border-amber-500/20">
              <div className="text-lg font-bold text-amber-400">
                {comparisonData.total_sprawl_ms}ms
              </div>
              <div className="text-[10px] text-text-secondary/50">Sprawl (4 DBs)</div>
              {comparisonData.sprawl_errors > 0 && (
                <div className="text-[10px] text-red-400 mt-0.5">
                  {comparisonData.sprawl_errors} error{comparisonData.sprawl_errors > 1 ? "s" : ""}
                </div>
              )}
            </div>
          </div>
          {comparisonData.total_converged_ms > 0 && (
            <div className="text-center text-[10px] text-text-secondary/60 mt-1">
              Sprawl is{" "}
              <span
                className={
                  comparisonData.total_sprawl_ms > comparisonData.total_converged_ms
                    ? "text-red-400"
                    : "text-green-400"
                }
              >
                {(comparisonData.total_sprawl_ms / comparisonData.total_converged_ms).toFixed(1)}x
              </span>{" "}
              {comparisonData.total_sprawl_ms > comparisonData.total_converged_ms
                ? "slower"
                : "faster"}{" "}
              across {comparisonData.tool_count} tool calls
            </div>
          )}

          {/* Operational pain indicators */}
          <div className="border-t border-white/5 pt-2 mt-2 space-y-1">
            <span className="text-text-secondary font-medium text-[10px] uppercase tracking-wider">
              Operational Overhead
            </span>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] mt-1">
              <div className="text-text-secondary/60">Connection pools</div>
              <div className="text-right">
                <span className="text-blue-400">1</span>
                <span className="text-text-secondary/30 mx-1">vs</span>
                <span className="text-amber-400">4</span>
              </div>
              <div className="text-text-secondary/60">Failure domains</div>
              <div className="text-right">
                <span className="text-blue-400">1</span>
                <span className="text-text-secondary/30 mx-1">vs</span>
                <span className="text-amber-400">4</span>
              </div>
              <div className="text-text-secondary/60">Network round-trips</div>
              <div className="text-right">
                <span className="text-blue-400">1</span>
                <span className="text-text-secondary/30 mx-1">vs</span>
                <span className="text-amber-400">{comparisonData.tool_count}</span>
              </div>
              <div className="text-text-secondary/60">Query languages</div>
              <div className="text-right">
                <span className="text-blue-400">SQL</span>
                <span className="text-text-secondary/30 mx-1">vs</span>
                <span className="text-amber-400">SQL+Cypher+REST</span>
              </div>
              <div className="text-text-secondary/60">Transaction scope</div>
              <div className="text-right">
                <span className="text-blue-400">ACID</span>
                <span className="text-text-secondary/30 mx-1">vs</span>
                <span className="text-amber-400">eventual</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
