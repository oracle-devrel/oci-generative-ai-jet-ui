import { ShieldCheck, Sparkles, MapPin, EyeOff, Lock, Globe2, Ban } from "lucide-react";

const CLEARANCE_BADGE = {
  EXECUTIVE: "bg-accent-tool/20 text-accent-tool border-accent-tool/40",
  STANDARD: "bg-accent-skill/20 text-accent-skill border-accent-skill/40",
};

// Starter prompts per persona. Each entry has:
//   text     — the prompt the button sends as a chat message
//   tag      — optional pill: 'globe' | 'denied'. 'globe' means the World
//              panel reacts to this card — either the agent calls focus_world,
//              or the answer is regional and the globe follows automatically.
//   denyHint — when tag === 'denied', a 1-line explanation of which boundary
//              the question is expected to hit so the user understands the
//              red badge means "this is supposed to fail for this persona".
const STARTERS = {
  agent: [
    { text: "Briefly summarize the FINANCE schema — what entities and how they relate." },
    { text: "How many transactions were flagged or blocked by the AML rules in the last 90 days, and which regions and typologies drive them?",
      tag: "globe" },
    { text: "Which merchants attract the most flagged transactions, and where are they located?",
      tag: "globe" },
    { text: "Map the AML picture: flag counts by region and typology for the last 90 days.",
      tag: "globe" },
    { text: "Pull up the SAR narrative for customer 42 and summarize the investigation.",
      tag: "denied",
      denyHint: "SAR_REPORTS is compliance-only — this persona can't read it at all." },
  ],
  cfo: [
    { text: "What's the total transaction volume in USD over the last 90 days?" },
    { text: "Show me the top 5 branches by transaction count, with the average amount.",
      tag: "globe" },
    { text: "Compare all four regions side by side — volume, flagged counts, and the dominant AML typology in each.",
      tag: "globe" },
    { text: "Fly the globe to the Wall Street branch and tell me about its region.",
      tag: "globe" },
    { text: "Open AGENT.AGENT_AUTHORIZATIONS and list every persona's region access.",
      tag: "denied",
      denyHint: "even the CFO is forbidden from AGENT admin tables — those are internal-only." },
  ],
  "compliance.officer": [
    { text: "List the open SAR reports with their reason codes and customer risk ratings." },
    { text: "Which customers drive the most flagged transactions, and where are they based?",
      tag: "globe" },
    { text: "Which AML rules actually generate SAR filings, and how often does each rule fire?" },
    { text: "Fly the globe to BitVault Exchange and break down that merchant's flagged transactions by typology.",
      tag: "globe" },
    { text: "Open AGENT.AGENT_AUTHORIZATIONS and list every persona's region access.",
      tag: "denied",
      denyHint: "even compliance can't open AGENT admin tables." },
  ],
  "analyst.east": [
    { text: "Which branches in EUROPE or MIDDLE_EAST have the most flagged transactions?",
      tag: "globe" },
    { text: "What's the transaction mix by channel for my region over the last 90 days?" },
    { text: "Which AML typology dominates my region, and how concentrated is it?",
      tag: "globe" },
    { text: "Fly the globe to the EUROPE region and highlight flagged activity.",
      tag: "globe" },
    { text: "Show me the top AMERICAS transactions by amount — I want to compare against my region.",
      tag: "denied",
      denyHint: "analyst.east can't see AMERICAS rows, AND transaction amounts are masked for this clearance." },
  ],
  "analyst.west": [
    { text: "Which merchants in AMERICAS or ASIA_PACIFIC attract the most flagged activity?",
      tag: "globe" },
    { text: "List the casinos and crypto exchanges in my region.",
      tag: "globe" },
    { text: "Where are the RAPID_CASH_OUT cases concentrated, and which region and channel do they use?",
      tag: "globe" },
    { text: "Fly the globe to Marina Bay Sands and tell me how much flagged activity that casino has.",
      tag: "globe" },
    { text: "What's the total transaction value for EUROPE over the last 90 days?",
      tag: "denied",
      denyHint: "analyst.west can't see EUROPE rows — and amounts are masked for this clearance anyway." },
  ],
  "ops.viewer": [
    { text: "How many branches are in each region, and where are they?",
      tag: "globe" },
    { text: "Which merchants have the most flagged transactions in the last 120 days?",
      tag: "globe" },
    { text: "Which branches carry the most flagged or blocked transactions, and through which channels?",
      tag: "globe" },
    { text: "Fly the globe to our Dubai branch and zoom in.",
      tag: "globe" },
    { text: "Show me the customer record for the account with the highest balance.",
      tag: "denied",
      denyHint: "ops.viewer is forbidden from FINANCE.CUSTOMERS — operations only, no customer PII." },
  ],
};

const FALLBACK_STARTERS = [
  { text: "What's in the FINANCE schema?" },
  { text: "How many transactions were flagged in the last 90 days?" },
];

const TAG_META = {
  globe:  { icon: Globe2,    label: "globe",     cls: "bg-accent-memory/15 text-accent-memory border-accent-memory/30" },
  denied: { icon: Ban,       label: "expected: denied", cls: "bg-accent-sql/15 text-accent-sql border-accent-sql/40" },
};

/**
 * Shown in the chat pane before the first message of a thread. Describes the
 * acting persona (clearance / regions / masks / forbidden tables) and offers
 * starter-prompt buttons calibrated to what that persona can actually see.
 *
 * Every card is calibrated to return real insight for a first-time user — no
 * dead ends and no cards that depend on an optional API key:
 *   • Globe-driving questions tagged "globe" — some call focus_world
 *     explicitly, the rest are regional answers the globe follows on its own.
 *   • One question deliberately calibrated to FAIL for this persona's
 *     authorization rules — flagged with a red "expected: denied" chip so the
 *     user learns where the boundary is.
 */
export default function WelcomeMat({ identity, onStart, disabled = false }) {
  if (!identity) return null;
  const starters = STARTERS[identity.id] || FALLBACK_STARTERS;
  const clearanceCls =
    CLEARANCE_BADGE[identity.clearance] ||
    "bg-text-secondary/20 text-text-secondary border-text-secondary/40";

  return (
    <div className="max-w-3xl mx-auto mt-6 mb-8">
      <div className="bg-bg-elev border border-white/5 rounded-lg overflow-hidden">
        {/* Persona header */}
        <div className="px-5 py-4 border-b border-white/5 bg-gradient-to-r from-bg-panel/80 to-bg-elev">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck size={16} className="text-accent-oracle" />
            <span className="text-[10px] uppercase tracking-wider text-text-muted">
              You are acting as
            </span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-semibold text-text-primary">
              {identity.label}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono border ${clearanceCls}`}>
              {identity.clearance}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-white/[0.05] text-text-secondary">
              id: {identity.id}
            </span>
          </div>
          <p className="mt-2 text-[13px] text-text-accent leading-snug">
            {identity.description}
          </p>
        </div>

        {/* Restriction summary */}
        <div className="px-5 py-3 grid grid-cols-1 sm:grid-cols-3 gap-3 border-b border-white/5">
          <RestrictionTile
            icon={<MapPin size={12} className="text-accent-skill" />}
            label="Authorized regions"
            items={identity.regions || ["all regions"]}
            allOpenLabel="all regions"
          />
          <RestrictionTile
            icon={<EyeOff size={12} className="text-accent-sql" />}
            label="Masked columns"
            items={(identity.mask_cols || []).map((c) => c.split(".").slice(-2).join("."))}
            emptyLabel="none — every column visible"
          />
          <RestrictionTile
            icon={<Lock size={12} className="text-accent-sql" />}
            label="Forbidden tables"
            items={(identity.forbid_tables || []).map((c) => c.split(".").slice(-2).join("."))}
            emptyLabel="none — every table readable"
          />
        </div>

        {/* Starters */}
        <div className="px-5 py-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles size={12} className="text-accent-tool" />
              <span className="text-[10px] uppercase tracking-wider text-text-muted">
                Starter questions for this role
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-text-muted">
              <Legend />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {starters.map((q) => (
              <StarterButton key={q.text} q={q} onStart={onStart} disabled={disabled} />
            ))}
          </div>
          <p className="mt-3 text-[10px] text-text-muted">
            Click a card to send it as your first message — or type your own
            below. Cards tagged <span className="text-accent-memory">globe</span>{" "}
            make the World panel react: some fly the camera explicitly, the rest
            are regional answers the globe follows automatically. Cards marked{" "}
            <span className="text-accent-sql">expected: denied</span>{" "}
            intentionally hit this persona's authorization boundary so you can
            see how the agent surfaces the denial. Switch persona in the
            header to change what you can see.
          </p>
        </div>
      </div>
    </div>
  );
}

function StarterButton({ q, onStart, disabled }) {
  const meta = q.tag ? TAG_META[q.tag] : null;
  const Icon = meta?.icon;
  const borderCls = q.tag === "denied"
    ? "border-accent-sql/30 hover:border-accent-sql"
    : "border-white/[0.06] hover:border-accent-oracle/40";
  return (
    <button
      onClick={() => onStart(q.text)}
      disabled={disabled}
      className={`text-left text-[12px] leading-snug px-3 py-2 rounded border bg-white/[0.02] hover:bg-white/[0.06] text-text-accent disabled:opacity-40 disabled:cursor-not-allowed ${borderCls}`}
      title={disabled ? "the agent is still working on another thread" : q.denyHint || undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <span>{q.text}</span>
        {meta && (
          <span className={`shrink-0 inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded font-mono border ${meta.cls}`}>
            {Icon ? <Icon size={9} /> : null}
            {meta.label}
          </span>
        )}
      </div>
      {q.tag === "denied" && q.denyHint && (
        <div className="mt-1 text-[10px] text-accent-sql/80 italic">
          {q.denyHint}
        </div>
      )}
    </button>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {Object.entries(TAG_META).map(([k, m]) => {
        const Icon = m.icon;
        return (
          <span
            key={k}
            className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded font-mono border ${m.cls}`}
          >
            <Icon size={9} />
            {m.label}
          </span>
        );
      })}
    </div>
  );
}

function RestrictionTile({ icon, label, items, emptyLabel, allOpenLabel }) {
  return (
    <div className="bg-bg-panel/40 rounded p-2.5 border border-white/[0.04]">
      <div className="flex items-center gap-1.5 mb-1.5">
        {icon}
        <span className="text-[10px] uppercase tracking-wider text-text-muted">
          {label}
        </span>
      </div>
      <div className="flex flex-wrap gap-1">
        {items.length === 0 || (items.length === 1 && items[0] === allOpenLabel) ? (
          items.length === 0 ? (
            <span className="text-[10px] text-text-secondary italic">
              {emptyLabel}
            </span>
          ) : (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-memory/15 text-accent-memory font-mono">
              {items[0]}
            </span>
          )
        ) : (
          items.map((it) => (
            <span
              key={it}
              className="text-[10px] px-1.5 py-0.5 rounded bg-accent-skill/10 text-text-accent font-mono border border-white/5"
            >
              {it}
            </span>
          ))
        )}
      </div>
    </div>
  );
}
