import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  CheckCircle2,
  ChevronRight,
  Code2,
  Database,
  FileText,
  Gauge,
  GitBranch,
  Layers3,
  Loader2,
  Network,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Table2,
} from "lucide-react";

import type {
  AppStatus,
  AskResponse,
  CorpusResponse,
  OracleInspectionResponse,
  RetrievalMode,
  SeedResponse,
  WorkflowStep,
} from "@oracle-langchain-js-rag/shared";

import {
  askQuestion,
  getCorpus,
  getOracleInspection,
  getStatus,
  resetCorpus,
  seedCorpus,
} from "./api";

const sampleQuestions = [
  "How do I use OracleVS with LangChain.js in a TypeScript RAG app?",
  "How do metadata filters improve retrieval?",
  "How should I fix ORA-28001 when running this Node.js sample?",
  "When should I use MMR instead of similarity search?",
];

const defaultQuestion = sampleQuestions[0] ?? "";
const tabs = ["Technical Flow", "Live Assistant", "Oracle Table"] as const;

const architectureNodes = [
  {
    id: "ui",
    label: "React UI",
    headline: "Developer asks a question",
    detail: "The front end collects the question, metadata filter, retrieval mode, and top K so the developer can compare RAG behavior without changing code.",
    capability: "LangChain workflow is exposed as a runnable TypeScript app, not a notebook.",
    file: "apps/web/src/App.tsx",
    icon: Search,
  },
  {
    id: "api",
    label: "Node.js API",
    headline: "Hono routes orchestrate the request",
    detail: "The API validates input, loads root environment configuration, checks Oracle, and calls the shared RAG service.",
    capability: "This is the intended JavaScript/TypeScript runtime for the sample.",
    file: "services/api/src/app.ts",
    icon: Network,
  },
  {
    id: "langchain",
    label: "LangChain.js",
    headline: "Documents, embeddings, retrievers, and LLM call",
    detail: "The core package builds LangChain Document chunks, creates embeddings, runs OracleVS retrieval, and prepares grounded context for the model.",
    capability: "Demonstrates the RAG building blocks developers expect from LangChain.js.",
    file: "packages/core/src/rag.ts",
    icon: GitBranch,
  },
  {
    id: "embeddings",
    label: "Embeddings",
    headline: "Text becomes vectors",
    detail: "The demo uses deterministic TypeScript embeddings for reproducible local runs, while the code path can be swapped for OpenAI, OCI, or another LangChain embedding implementation.",
    capability: "Shows the embedding interface and the query vector preview.",
    file: "packages/core/src/demoEmbeddings.ts",
    icon: Gauge,
  },
  {
    id: "oracle",
    label: "OracleVS",
    headline: "Oracle AI Database stores vectors and metadata",
    detail: "OracleVS persists text, metadata, and vector embeddings in an Oracle table, then performs similarity or MMR retrieval with optional metadata filtering.",
    capability: "Highlights Oracle AI Database as the vector store behind LangChain.js.",
    file: "packages/db/src/vectorStore.ts",
    icon: Database,
  },
  {
    id: "answer",
    label: "Grounded Answer",
    headline: "The LLM answers from retrieved evidence",
    detail: "The answer step receives only retrieved OracleVS evidence and returns a practical developer response with source chunk citations.",
    capability: "Connects retrieval to LLM generation while keeping the evidence inspectable.",
    file: "packages/core/src/rag.ts",
    icon: CheckCircle2,
  },
] as const;

type BusyAction = "status" | "seed" | "reset" | "ask" | "inspect" | null;
type Tab = (typeof tabs)[number];
type ArchitectureNode = (typeof architectureNodes)[number];
type ArchitectureNodeId = ArchitectureNode["id"];

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={ok ? "badge badge-ok" : "badge badge-warn"}>
      {ok ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
      {label}
    </span>
  );
}

function LoadingIcon({ show }: { show: boolean }) {
  return show ? <Loader2 className="spin" size={16} /> : null;
}

function StepPill({ step }: { step: WorkflowStep }) {
  const ok = step.status === "PASS" || step.status === "READY";
  return (
    <li className="step-pill">
      <span className={ok ? "dot dot-ok" : "dot dot-warn"} />
      <strong>{step.step}</strong>
      <small>{step.status}</small>
      <p>{step.detail}</p>
    </li>
  );
}

function TechnicalFlowPanel({
  corpus,
  result,
  status,
}: {
  corpus: CorpusResponse | null;
  result: AskResponse | null;
  status: AppStatus | null;
}) {
  const [activeNodeId, setActiveNodeId] = useState<ArchitectureNodeId>("langchain");
  const activeNode = architectureNodes.find((node) => node.id === activeNodeId) ?? architectureNodes[2];

  return (
    <section className="tab-stack">
      <section className="flow-hero">
        <div className="flow-copy">
          <p className="eyebrow">Interactive technical map</p>
          <h2>LangChain.js RAG running against Oracle AI Database</h2>
          <p className="lead">
            This view follows one developer question through the TypeScript app: UI input, Node.js API,
            LangChain.js retrieval, OracleVS vector search, and grounded LLM answer.
          </p>
          <div className="capability-strip" aria-label="Implemented LangChain.js capabilities">
            <span>Documents</span>
            <span>Embeddings</span>
            <span>OracleVS</span>
            <span>Similarity</span>
            <span>MMR</span>
            <span>Metadata filters</span>
            <span>Grounded answer</span>
          </div>
        </div>

        <div className="architecture-stage" aria-label="Interactive LangChain.js Oracle architecture map">
          <div className="stage-grid" />
          <svg className="flow-connectors" viewBox="0 0 1000 360" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto">
                <path d="M0,0 L10,4 L0,8 Z" />
              </marker>
            </defs>
            <path d="M125 108 C200 108 205 242 295 242" />
            <path d="M295 242 C365 242 405 108 475 108" />
            <path d="M475 108 C550 108 580 242 655 242" />
            <path d="M655 242 C725 242 730 108 800 108" />
            <path d="M800 108 C850 108 855 242 905 242" />
          </svg>
          {architectureNodes.map((node, index) => {
            const Icon = node.icon;
            return (
              <button
                className={node.id === activeNode.id ? "flow-node active" : "flow-node"}
                data-node={node.id}
                key={node.id}
                onClick={() => setActiveNodeId(node.id)}
                onMouseEnter={() => setActiveNodeId(node.id)}
                style={{ "--node-index": index } as React.CSSProperties}
                type="button"
              >
                <span className="node-orb">
                  <Icon size={22} />
                </span>
                <strong>{node.label}</strong>
              </button>
            );
          })}
        </div>
      </section>

      <section className="flow-detail-grid">
        <article className="panel active-node-panel">
          <div className="panel-heading">
            <Layers3 size={19} />
            <h2>{activeNode.headline}</h2>
          </div>
          <p>{activeNode.detail}</p>
          <dl className="detail-list">
            <div>
              <dt>Capability</dt>
              <dd>{activeNode.capability}</dd>
            </div>
            <div>
              <dt>Code path</dt>
              <dd>{activeNode.file}</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <Boxes size={19} />
            <h2>Runtime snapshot</h2>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Oracle</dt>
              <dd>{status?.database.detail ?? "Waiting for API status"}</dd>
            </div>
            <div>
              <dt>Knowledge base</dt>
              <dd>{corpus ? `${corpus.totalDocuments} chunks from ${corpus.totalSources} sources` : "Loading corpus"}</dd>
            </div>
            <div>
              <dt>Latest retrieval</dt>
              <dd>{result ? `${result.retrieved.length} chunks via ${result.retrievalMode}` : "Run a question in Live Assistant"}</dd>
            </div>
          </dl>
        </article>
      </section>
    </section>
  );
}

function LiveAssistantPanel({
  busy,
  categories,
  category,
  corpus,
  k,
  question,
  result,
  retrievalMode,
  setCategory,
  setK,
  setQuestion,
  setRetrievalMode,
  onAsk,
}: {
  busy: BusyAction;
  categories: string[];
  category: string;
  corpus: CorpusResponse | null;
  k: number;
  question: string;
  result: AskResponse | null;
  retrievalMode: RetrievalMode;
  setCategory: (value: string) => void;
  setK: (value: number) => void;
  setQuestion: (value: string) => void;
  setRetrievalMode: (value: RetrievalMode) => void;
  onAsk: () => void;
}) {
  return (
    <section className="tab-stack">
      <section className="workspace-grid">
        <form
          className="panel ask-panel"
          onSubmit={(event) => {
            event.preventDefault();
            onAsk();
          }}
        >
          <div className="panel-heading">
            <SlidersHorizontal size={19} />
            <h2>Ask the TypeScript RAG assistant</h2>
          </div>

          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={5}
            aria-label="Question"
          />

          <div className="quick-row">
            {sampleQuestions.map((sample) => (
              <button key={sample} type="button" className="chip" onClick={() => setQuestion(sample)}>
                {sample}
              </button>
            ))}
          </div>

          <div className="control-row">
            <label>
              Metadata filter
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Top K
              <input min={1} max={8} type="number" value={k} onChange={(event) => setK(Number(event.target.value))} />
            </label>
            <label>
              Retrieval mode
              <select value={retrievalMode} onChange={(event) => setRetrievalMode(event.target.value as RetrievalMode)}>
                <option value="similarity">similarity with score</option>
                <option value="mmr">MMR diversity</option>
              </select>
            </label>
          </div>

          <button className="primary ask-button" type="submit" disabled={busy !== null || !question.trim()}>
            <Play size={17} />
            Ask
            <LoadingIcon show={busy === "ask"} />
          </button>
        </form>

        <aside className="panel trace-card">
          <div className="panel-heading">
            <Layers3 size={19} />
            <h2>RAG execution trace</h2>
          </div>
          <ol className="step-list">
            {(result?.summary ?? [
              { step: "seed", status: "READY", detail: "Seed the markdown knowledge base into OracleVS." },
              { step: "retrieve", status: "READY", detail: "Run similarity or MMR retrieval from Oracle AI Database." },
              { step: "answer", status: "READY", detail: "Ground the LLM answer in retrieved evidence." },
            ]).map((step) => (
              <StepPill key={step.step} step={step as WorkflowStep} />
            ))}
          </ol>
          <div className="mini-stat-row">
            <span>{corpus?.totalDocuments ?? 0} chunks</span>
            <span>{corpus?.embeddingDimension ?? 12} dimensions</span>
            <span>{retrievalMode}</span>
          </div>
        </aside>
      </section>

      <section className="answer-layout">
        <article className="panel answer-panel">
          <div className="panel-heading">
            <CheckCircle2 size={19} />
            <h2>Grounded answer</h2>
          </div>
          <pre>{result?.answer ?? "Run a question to see the answer generated from OracleVS evidence."}</pre>
        </article>

        <article className="panel evidence-panel">
          <div className="panel-heading">
            <BookOpen size={19} />
            <h2>Evidence used</h2>
          </div>
          <div className="result-list">
            {(result?.retrieved ?? []).map((doc) => (
              <article className="result-card" key={`${doc.rank}-${doc.source}-${doc.section}`}>
                <div className="result-card-header">
                  <strong>#{doc.rank} {doc.title}</strong>
                  <span>{typeof doc.distance === "number" ? `distance ${doc.distance}` : "MMR selected"}</span>
                </div>
                <p>{doc.snippet}</p>
                <div className="metadata-row">
                  <span>{doc.section}</span>
                  <span>{doc.category}</span>
                  <span>{doc.product}</span>
                  {doc.tags.slice(0, 2).map((tag) => (
                    <span key={`${doc.rank}-${tag}`}>{tag}</span>
                  ))}
                </div>
              </article>
            ))}
            {!result ? <p className="empty-state">Retrieved OracleVS evidence will appear here, not raw prompt context.</p> : null}
          </div>
        </article>
      </section>

      <section className="trace-grid">
        <article className="panel code-panel">
          <div className="panel-heading">
            <Code2 size={19} />
            <h2>LangChain.js call</h2>
          </div>
          <pre>{result?.trace.retrieval.langchainCall ?? "vectorStore.similaritySearchWithScore(question, k, filter)\nvectorStore.maxMarginalRelevanceSearch(question, { k, fetchK, lambda, filter })"}</pre>
        </article>
        <article className="panel code-panel">
          <div className="panel-heading">
            <Database size={19} />
            <h2>Representative Oracle vector search</h2>
          </div>
          <pre>{result?.trace.retrieval.representativeSql ?? "Run a query to show the representative VECTOR_DISTANCE SQL."}</pre>
        </article>
      </section>
    </section>
  );
}

function OracleTablePanel({
  inspection,
  result,
  status,
}: {
  inspection: OracleInspectionResponse | null;
  result: AskResponse | null;
  status: AppStatus | null;
}) {
  const vectorIndexes = inspection?.inspection?.indexes.filter((index) => index.category === "vector") ?? [];

  return (
    <section className="tab-stack">
      <section className="inspector-grid">
        <article className="panel">
          <div className="panel-heading">
            <Table2 size={19} />
            <h2>OracleVS table</h2>
          </div>
          <dl className="detail-list">
            <div>
              <dt>Table</dt>
              <dd>{inspection?.tableName ?? status?.config.tableName ?? "LC_JS_RAG_DEMO"}</dd>
            </div>
            <div>
              <dt>Rows</dt>
              <dd>{inspection?.inspection?.rowCount ?? "Seed first"}</dd>
            </div>
            <div>
              <dt>Connection</dt>
              <dd>{inspection?.detail ?? status?.database.detail ?? "Checking..."}</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <Gauge size={19} />
            <h2>Vector index</h2>
          </div>
          <div className="schema-list">
            {vectorIndexes.map((index) => (
              <span key={index.index}>
                <strong>{index.index}</strong>
                <small>{index.category} / {index.type}</small>
              </span>
            ))}
            {vectorIndexes.length === 0 ? <p className="empty-state">No vector index metadata returned yet. Set ORACLE_CREATE_VECTOR_INDEX=true, then run Seed.</p> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <FileText size={19} />
            <h2>Columns</h2>
          </div>
          <div className="schema-list">
            {(inspection?.inspection?.columns ?? []).map((column) => (
              <span key={column.column}>
                <strong>{column.column}</strong>
                <small>{column.type}</small>
              </span>
            ))}
            {!inspection?.inspection?.columns.length ? <p className="empty-state">Seed the table to inspect columns.</p> : null}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <Gauge size={19} />
          <h2>Query vector preview</h2>
        </div>
        <p className="subtle-copy">
          The UI shows a short preview of the query embedding so developers can connect the question,
          LangChain embeddings, OracleVS retrieval, and Oracle vector search in one place.
        </p>
        <div className="vector-row">
          {(result?.trace.embedding.preview ?? []).map((value, index) => (
            <span key={`${value}-${index}`}>{value}</span>
          ))}
          {!result ? <p className="empty-state">Run a query in Live Assistant to see the embedding preview.</p> : null}
        </div>
      </section>
    </section>
  );
}

export function App() {
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [corpus, setCorpus] = useState<CorpusResponse | null>(null);
  const [inspection, setInspection] = useState<OracleInspectionResponse | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [seedResult, setSeedResult] = useState<SeedResponse | null>(null);
  const [question, setQuestion] = useState(defaultQuestion);
  const [category, setCategory] = useState("all");
  const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>("similarity");
  const [k, setK] = useState(4);
  const [busy, setBusy] = useState<BusyAction>("status");
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Technical Flow");

  async function refreshStatus() {
    setBusy("status");
    setError(null);
    try {
      const [nextStatus, nextCorpus, nextInspection] = await Promise.all([
        getStatus(),
        getCorpus(),
        getOracleInspection().catch(() => null),
      ]);
      setStatus(nextStatus);
      setCorpus(nextCorpus);
      if (nextInspection) {
        setInspection(nextInspection);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function refreshInspection() {
    setBusy("inspect");
    setError(null);
    try {
      setInspection(await getOracleInspection());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    void refreshStatus();
  }, []);

  const categories = useMemo(() => {
    const values = new Set(["all"]);
    for (const doc of corpus?.documents ?? []) {
      if (doc.category) values.add(doc.category);
    }
    return Array.from(values);
  }, [corpus]);

  async function handleSeed() {
    setBusy("seed");
    setError(null);
    try {
      const seeded = await seedCorpus();
      setSeedResult(seeded);
      await refreshStatus();
      await refreshInspection();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleReset() {
    setBusy("reset");
    setError(null);
    try {
      await resetCorpus();
      setResult(null);
      setSeedResult(null);
      setInspection(null);
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleAsk() {
    setBusy("ask");
    setError(null);
    try {
      const answer = await askQuestion({ question, k, category, retrievalMode });
      setResult(answer);
      setActiveTab("Live Assistant");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  const configured = Boolean(status?.config.oracleConfigured);
  const connected = Boolean(status?.database.connected);

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Oracle AI Database + LangChain.js</p>
          <h1>Oracle LangChain.js Developer Assistant</h1>
        </div>
        <div className="header-actions">
          <button className="icon-button" title="Refresh status" onClick={refreshStatus} disabled={busy !== null}>
            <RefreshCw size={18} />
          </button>
          <button className="secondary" onClick={handleReset} disabled={busy !== null}>
            <RotateCcw size={16} />
            Reset
            <LoadingIcon show={busy === "reset"} />
          </button>
          <button className="primary" onClick={handleSeed} disabled={busy !== null || !configured}>
            <Database size={16} />
            Seed
            <LoadingIcon show={busy === "seed"} />
          </button>
        </div>
      </header>

      <section className="status-band">
        <StatusBadge ok={configured} label={configured ? "Config ready" : "Config missing"} />
        <StatusBadge ok={connected} label={connected ? "Oracle connected" : "Oracle offline"} />
        <StatusBadge ok={Boolean(status?.config.openAiConfigured)} label={status?.config.openAiConfigured ? "LLM enabled" : "Extractive mode"} />
        <StatusBadge ok={Boolean(status?.config.createVectorIndex)} label={status?.config.createVectorIndex ? "Vector index requested" : "Vector index optional"} />
        <span className="table-pill">{status?.config.tableName ?? "LC_JS_RAG_DEMO"}</span>
      </section>

      {error ? (
        <section className="error-band">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </section>
      ) : null}

      <nav className="tab-nav" aria-label="Developer assistant sections">
        {tabs.map((tab) => (
          <button key={tab} className={activeTab === tab ? "tab-button active" : "tab-button"} onClick={() => setActiveTab(tab)}>
            {tab}
          </button>
        ))}
      </nav>

      {activeTab === "Technical Flow" ? <TechnicalFlowPanel corpus={corpus} result={result} status={status} /> : null}
      {activeTab === "Live Assistant" ? (
        <LiveAssistantPanel
          busy={busy}
          categories={categories}
          category={category}
          corpus={corpus}
          k={k}
          question={question}
          result={result}
          retrievalMode={retrievalMode}
          setCategory={setCategory}
          setK={setK}
          setQuestion={setQuestion}
          setRetrievalMode={setRetrievalMode}
          onAsk={() => void handleAsk()}
        />
      ) : null}
      {activeTab === "Oracle Table" ? (
        <OracleTablePanel inspection={inspection} result={result} status={status} />
      ) : null}

      <footer className="app-footer">
        <span>{seedResult ? `Last seed inserted ${seedResult.documentsIndexed} chunks.` : "Use Technical Flow for architecture screenshots, then Live Assistant for the runnable RAG workflow."}</span>
        <button className="secondary" onClick={refreshInspection} disabled={busy !== null || !configured}>
          <Table2 size={16} />
          Inspect Oracle
          <LoadingIcon show={busy === "inspect"} />
        </button>
      </footer>
    </main>
  );
}
