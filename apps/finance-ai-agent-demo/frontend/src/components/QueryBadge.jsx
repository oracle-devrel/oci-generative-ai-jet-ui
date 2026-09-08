const BADGE_CONFIG = {
  vector: { label: "VECTOR SEARCH", className: "badge-vector" },
  relational: { label: "RELATIONAL", className: "badge-relational" },
  graph: { label: "GRAPH TRAVERSAL", className: "badge-graph" },
  hybrid: { label: "HYBRID SEARCH", className: "badge-hybrid" },
  convergent: { label: "CONVERGENT", className: "badge-convergent" },
  json: { label: "JSON/DOCUMENT", className: "badge-json" },
  text: { label: "TEXT SEARCH", className: "badge-text" },
  spatial: { label: "SPATIAL", className: "badge-spatial" },
};

export default function QueryBadge({ type }) {
  const config = BADGE_CONFIG[type] || BADGE_CONFIG.relational;

  return (
    <span
      className={`inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded-full ${config.className}`}
    >
      {config.label}
    </span>
  );
}
