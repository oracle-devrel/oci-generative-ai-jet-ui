import "server-only";

import oracledb, { type Connection, type Pool } from "oracledb";

import {
  DataChatApiResponseSchema,
  DataChatPlanSchema,
  type DataChatApiResponse,
  type DataChatPlan,
  type QueryTrace,
  type UiComponent
} from "./schemas";

export type DataChatProgress = {
  phase: "model" | "oracle" | "render";
  message: string;
  detail?: string;
};

type RunDataChatOptions = {
  onProgress?: (progress: DataChatProgress) => void;
  signal?: AbortSignal;
};

type DatabaseRow = Record<string, unknown>;
type QueryResult = {
  rows: DatabaseRow[];
  elapsedMs: number;
};

const globalForOracle = globalThis as typeof globalThis & {
  dataChatPool?: Promise<Pool>;
};

oracledb.fetchAsString = [oracledb.CLOB];

const REVENUE_SQL = `
SELECT TO_CHAR(month_start, 'Mon YYYY') AS month,
       revenue,
       pipeline,
       expansion,
       churn,
       note
FROM (
  SELECT month_start, revenue, pipeline, expansion, churn, note
  FROM revenue_metrics
  ORDER BY month_start DESC
  FETCH FIRST 12 ROWS ONLY
)
ORDER BY month_start`;

const TOP_ACCOUNTS_SQL = `
SELECT account_name,
       region,
       segment,
       q1_revenue,
       active_contracts
FROM accounts
WHERE fiscal_quarter = 'Q1'
ORDER BY q1_revenue DESC
FETCH FIRST 5 ROWS ONLY`;

const ACTIVE_USERS_SQL = `
SELECT TO_CHAR(month_start, 'Mon YYYY') AS month,
       active_users
FROM (
  SELECT month_start, active_users
  FROM active_user_metrics
  ORDER BY month_start DESC
  FETCH FIRST 7 ROWS ONLY
)
ORDER BY month_start`;

const CONTRACT_VECTOR_SQL = `
SELECT chunk_id,
       account_name,
       contract_title,
       chunk_text,
       citation_label,
       VECTOR_DISTANCE(embedding, TO_VECTOR(:queryEmbedding), COSINE) AS distance
FROM contract_chunks
ORDER BY VECTOR_DISTANCE(embedding, TO_VECTOR(:queryEmbedding), COSINE)
FETCH FIRST 5 ROWS ONLY`;

const MARCH_REVENUE_SQL = `
SELECT TO_CHAR(month_start, 'Mon YYYY') AS month,
       revenue,
       pipeline,
       expansion,
       churn,
       note
FROM revenue_metrics
WHERE month_start BETWEEN DATE '2025-12-01' AND DATE '2026-04-30'
ORDER BY month_start`;

const MARCH_HYBRID_SQL = `
SELECT chunk_id,
       account_name,
       contract_title,
       chunk_text,
       citation_label,
       LEAST(
         1,
         0.6 * (1 - VECTOR_DISTANCE(embedding, TO_VECTOR(:queryEmbedding), COSINE)) +
         0.4 * (SCORE(1) / 100)
       ) AS hybrid_score
FROM contract_chunks
WHERE CONTAINS(chunk_text, :textQuery, 1) > 0
ORDER BY hybrid_score DESC
FETCH FIRST 5 ROWS ONLY`;

const DEFAULT_LLM_MODEL = "xai.grok-4.3";

const AUTO_RENEWAL_VECTOR = "[0.95,0.87,0.13,0.05,0.09,0.04,0.03,0.02]";
const MARCH_DIP_VECTOR = "[0.10,0.14,0.90,0.83,0.72,0.10,0.05,0.03]";

function report(options: RunDataChatOptions, progress: DataChatProgress) {
  options.onProgress?.(progress);
}

function assertNotAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw new DOMException("The data chat request was cancelled.", "AbortError");
  }
}

async function getPool() {
  if (!globalForOracle.dataChatPool) {
    globalForOracle.dataChatPool = oracledb.createPool({
      user: process.env.ORACLE_USER || "DATA_CHAT",
      password: process.env.ORACLE_PASSWORD || "DataChatPwd_2026",
      connectionString: process.env.ORACLE_CONNECTION_STRING || "127.0.0.1:1522/FREEPDB1",
      program: "devrel-developerhub-generative-ui-data-chat",
      poolMin: 0,
      poolMax: 4,
      poolIncrement: 1
    });
  }

  return globalForOracle.dataChatPool;
}

async function withConnection<T>(operation: (connection: Connection) => Promise<T>) {
  const pool = await getPool();
  const connection = await pool.getConnection();

  try {
    return await operation(connection);
  } finally {
    await connection.close();
  }
}

async function executeQuery(statement: string, binds: Record<string, unknown>, signal?: AbortSignal): Promise<QueryResult> {
  assertNotAborted(signal);
  const startedAt = performance.now();
  const rows = await withConnection(async (connection) => {
    const result = await connection.execute(statement, binds, {
      outFormat: oracledb.OUT_FORMAT_OBJECT
    });
    return result.rows ?? [];
  });
  assertNotAborted(signal);

  return {
    rows,
    elapsedMs: Math.max(0, Math.round(performance.now() - startedAt))
  };
}

function stringValue(row: DatabaseRow, key: string) {
  const value = row[key];
  return value == null ? "" : String(value);
}

function numberValue(row: DatabaseRow, key: string) {
  const value = row[key];
  const number = typeof value === "number" ? value : Number(value);
  return Number.isFinite(number) ? number : 0;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function formatCompactCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2
  }).format(value);
}

function percentChange(current: number, previous: number) {
  return previous === 0 ? 0 : ((current - previous) / previous) * 100;
}

function signedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function extractJson(content: string) {
  const withoutFence = content.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  const start = withoutFence.indexOf("{");
  const end = withoutFence.lastIndexOf("}");

  if (start < 0 || end <= start) {
    throw new Error("The planning model did not return a JSON object.");
  }

  return JSON.parse(withoutFence.slice(start, end + 1)) as unknown;
}

function expectedStrategy(intent: DataChatPlan["intent"]): DataChatPlan["strategy"] {
  if (intent === "contractSearch") {
    return "vector";
  }
  if (intent === "marchDip") {
    return "hybrid";
  }
  return "sql";
}

async function createPlan(message: string, signal?: AbortSignal): Promise<DataChatPlan> {
  const baseUrl = process.env.LLM_BASE_URL?.replace(/\/$/, "");
  const apiKey = process.env.LLM_API_KEY;
  const model = process.env.LLM_MODEL || DEFAULT_LLM_MODEL;

  if (!baseUrl || !apiKey) {
    throw new Error("LLM_BASE_URL and LLM_API_KEY must be configured.");
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    signal,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0,
      messages: [
        {
          role: "system",
          content: `You plan a safe Oracle data-chat demo. Return one JSON object and nothing else.

Choose exactly one intent:
- revenueTrend: revenue trends or a multi-component business dashboard (strategy sql)
- topAccounts: top accounts, regions, or Q1 rankings (strategy sql)
- activeUsers: current or historical active-user questions (strategy sql)
- contractSearch: contract clauses, renewal terms, or contract evidence (strategy vector)
- marchDip: explanations of the March revenue dip that combine metrics and evidence (strategy hybrid)

Allowed componentTypes: lineChart, areaChart, barChart, horizontalBarChart, pieChart, comparisonTable, kpiCard, sourceCards, mixedInsight.
Use mixedInsight only for marchDip and sourceCards for contractSearch. For a dashboard request, choose revenueTrend and several chart/table component types.

Required shape:
{"intent":"revenueTrend","strategy":"sql","title":"Revenue trend","componentTypes":["lineChart"]}`
        },
        { role: "user", content: message }
      ]
    })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Planning request failed (${response.status}): ${detail.slice(0, 300)}`);
  }

  const payload = (await response.json()) as {
    choices?: Array<{ message?: { content?: string | null } }>;
  };
  const content = payload.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error("The planning model returned an empty response.");
  }

  const plan = DataChatPlanSchema.parse(extractJson(content));
  return {
    ...plan,
    strategy: expectedStrategy(plan.intent)
  };
}

function trace(strategy: QueryTrace["strategy"], label: string, statement: string, result: QueryResult): QueryTrace {
  return {
    strategy,
    label,
    statement: statement.trim(),
    elapsedMs: result.elapsedMs,
    rowCount: result.rows.length
  };
}

function sourceCards(title: string, rows: DatabaseRow[], scoreKey: "DISTANCE" | "HYBRID_SCORE"): Extract<UiComponent, { type: "sourceCards" }> {
  return {
    type: "sourceCards",
    title,
    sources: rows.map((row) => {
      const rawScore = numberValue(row, scoreKey);
      const score = scoreKey === "DISTANCE" ? 1 - rawScore : rawScore;
      return {
        id: numberValue(row, "CHUNK_ID"),
        title: stringValue(row, "CONTRACT_TITLE"),
        account: stringValue(row, "ACCOUNT_NAME"),
        snippet: stringValue(row, "CHUNK_TEXT"),
        citation: stringValue(row, "CITATION_LABEL"),
        score: Math.max(0, Math.min(1, score))
      };
    })
  };
}

async function revenueAnswer(plan: DataChatPlan, signal?: AbortSignal) {
  const result = await executeQuery(REVENUE_SQL, {}, signal);
  const data = result.rows.map((row) => ({
    month: stringValue(row, "MONTH"),
    revenue: numberValue(row, "REVENUE"),
    pipeline: numberValue(row, "PIPELINE"),
    expansion: numberValue(row, "EXPANSION"),
    churn: numberValue(row, "CHURN")
  }));

  if (data.length === 0) {
    throw new Error("Oracle returned no revenue metrics. Run npm run db:seed first.");
  }

  const first = data[0];
  const latest = data[data.length - 1];
  const change = percentChange(latest.revenue, first.revenue);
  const requested = new Set(plan.componentTypes);
  const components: UiComponent[] = [];

  if (requested.has("areaChart")) {
    components.push({
      type: "areaChart",
      title: "Revenue and pipeline",
      description: "Monthly recognized revenue compared with pipeline value.",
      categoryKey: "month",
      data
    });
  }
  if (requested.has("barChart")) {
    components.push({
      type: "barChart",
      title: "Expansion and churn",
      description: "Monthly expansion contribution and churn pressure.",
      categoryKey: "month",
      variant: "grouped",
      data
    });
  }
  if (requested.has("pieChart")) {
    components.push({
      type: "pieChart",
      title: `${latest.month} revenue drivers`,
      description: "Latest expansion and churn values alongside recognized revenue.",
      categoryKey: "metric",
      dataKey: "value",
      variant: "donut",
      data: [
        { metric: "Revenue", value: latest.revenue },
        { metric: "Expansion", value: latest.expansion },
        { metric: "Churn", value: latest.churn }
      ]
    });
  }
  if (requested.has("comparisonTable")) {
    components.push({
      type: "comparisonTable",
      title: "Monthly revenue metrics",
      columns: [
        { key: "month", label: "Month" },
        { key: "revenue", label: "Revenue", align: "right" },
        { key: "pipeline", label: "Pipeline", align: "right" },
        { key: "expansion", label: "Expansion", align: "right" },
        { key: "churn", label: "Churn", align: "right" }
      ],
      rows: data.map((row) => ({
        month: row.month,
        revenue: formatCurrency(row.revenue),
        pipeline: formatCurrency(row.pipeline),
        expansion: formatCurrency(row.expansion),
        churn: formatCurrency(row.churn)
      }))
    });
  }
  if (requested.has("kpiCard")) {
    components.push({
      type: "kpiCard",
      title: `Revenue in ${latest.month}`,
      value: formatCompactCurrency(latest.revenue),
      delta: signedPercent(change),
      trend: change > 0 ? "up" : change < 0 ? "down" : "flat",
      caption: `Compared with ${formatCompactCurrency(first.revenue)} in ${first.month}`
    });
  }
  if (requested.has("lineChart") || components.length === 0) {
    components.unshift({
      type: "lineChart",
      title: plan.title,
      description: "Recognized revenue for the latest 12 seeded months.",
      xKey: "month",
      yKey: "revenue",
      data
    });
  }

  return {
    answer: {
      title: plan.title,
      summary: `Revenue reached ${formatCompactCurrency(latest.revenue)} in ${latest.month}, ${signedPercent(change)} versus ${first.month}.`,
      components
    },
    queryTrace: [trace("sql", "Revenue trend", REVENUE_SQL, result)]
  };
}

async function topAccountsAnswer(plan: DataChatPlan, signal?: AbortSignal) {
  const result = await executeQuery(TOP_ACCOUNTS_SQL, {}, signal);
  const data = result.rows.map((row) => ({
    account: stringValue(row, "ACCOUNT_NAME"),
    region: stringValue(row, "REGION"),
    segment: stringValue(row, "SEGMENT"),
    revenue: numberValue(row, "Q1_REVENUE"),
    contracts: numberValue(row, "ACTIVE_CONTRACTS")
  }));
  const leader = data[0];
  if (!leader) {
    throw new Error("Oracle returned no account metrics. Run npm run db:seed first.");
  }

  return {
    answer: {
      title: plan.title,
      summary: `${leader.account} leads Q1 at ${formatCompactCurrency(leader.revenue)}, followed by ${data.slice(1, 3).map((row) => row.account).join(" and ")}.`,
      components: [
        {
          type: "horizontalBarChart" as const,
          title: "Top Q1 accounts",
          description: "Accounts ranked by recognized Q1 revenue.",
          categoryKey: "account",
          variant: "grouped" as const,
          data
        },
        {
          type: "comparisonTable" as const,
          title: "Account comparison",
          columns: [
            { key: "account", label: "Account" },
            { key: "region", label: "Region" },
            { key: "segment", label: "Segment" },
            { key: "revenue", label: "Q1 revenue", align: "right" as const },
            { key: "contracts", label: "Contracts", align: "right" as const }
          ],
          rows: data.map((row) => ({ ...row, revenue: formatCurrency(row.revenue) }))
        }
      ]
    },
    queryTrace: [trace("sql", "Top Q1 accounts", TOP_ACCOUNTS_SQL, result)]
  };
}

async function activeUsersAnswer(plan: DataChatPlan, signal?: AbortSignal) {
  const result = await executeQuery(ACTIVE_USERS_SQL, {}, signal);
  const data = result.rows.map((row) => ({
    month: stringValue(row, "MONTH"),
    activeUsers: numberValue(row, "ACTIVE_USERS")
  }));
  const latest = data[data.length - 1];
  const previous = data[data.length - 2];
  if (!latest || !previous) {
    throw new Error("Oracle returned insufficient active-user history. Run npm run db:seed first.");
  }
  const change = percentChange(latest.activeUsers, previous.activeUsers);

  return {
    answer: {
      title: plan.title,
      summary: `Active users reached ${latest.activeUsers.toLocaleString("en-US")} in ${latest.month}, ${signedPercent(change)} month over month.`,
      components: [
        {
          type: "kpiCard" as const,
          title: "Active users",
          value: latest.activeUsers.toLocaleString("en-US"),
          delta: signedPercent(change),
          trend: change > 0 ? ("up" as const) : change < 0 ? ("down" as const) : ("flat" as const),
          caption: `Previous month: ${previous.activeUsers.toLocaleString("en-US")}`
        }
      ]
    },
    queryTrace: [trace("sql", "Active users month-over-month", ACTIVE_USERS_SQL, result)]
  };
}

async function contractSearchAnswer(plan: DataChatPlan, signal?: AbortSignal) {
  const result = await executeQuery(CONTRACT_VECTOR_SQL, { queryEmbedding: AUTO_RENEWAL_VECTOR }, signal);
  const sources = sourceCards("Relevant contract evidence", result.rows, "DISTANCE");

  return {
    answer: {
      title: plan.title,
      summary: `Oracle Vector Search found ${sources.sources.length} contract passages ranked by semantic similarity.`,
      components: [sources]
    },
    queryTrace: [trace("vector", "Semantic contract evidence", CONTRACT_VECTOR_SQL, result)]
  };
}

async function marchDipAnswer(plan: DataChatPlan, signal?: AbortSignal) {
  const [revenueResult, evidenceResult] = await Promise.all([
    executeQuery(MARCH_REVENUE_SQL, {}, signal),
    executeQuery(
      MARCH_HYBRID_SQL,
      {
        queryEmbedding: MARCH_DIP_VECTOR,
        textQuery: "March OR delayed OR renewal OR onboarding"
      },
      signal
    )
  ]);
  const data = revenueResult.rows.map((row) => ({
    month: stringValue(row, "MONTH"),
    revenue: numberValue(row, "REVENUE"),
    pipeline: numberValue(row, "PIPELINE")
  }));
  const march = data.find((row) => row.month === "Mar 2026");
  const february = data.find((row) => row.month === "Feb 2026");
  if (!march || !february) {
    throw new Error("Oracle returned insufficient March comparison data. Run npm run db:seed first.");
  }
  const change = percentChange(march.revenue, february.revenue);
  const sources = sourceCards("Evidence behind the March movement", evidenceResult.rows, "HYBRID_SCORE");

  return {
    answer: {
      title: plan.title,
      summary: `March revenue fell ${Math.abs(change).toFixed(1)}% month over month while pipeline remained ${formatCompactCurrency(march.pipeline)}. Contract evidence points to onboarding, procurement, and renewal timing rather than demand loss.`,
      components: [
        {
          type: "mixedInsight" as const,
          title: "March revenue diagnosis",
          callout: `Revenue moved from ${formatCompactCurrency(february.revenue)} in February to ${formatCompactCurrency(march.revenue)} in March, while the seeded evidence shows several milestones shifting into April.`,
          chart: {
            type: "lineChart" as const,
            title: "Revenue around the March dip",
            description: "Recognized revenue and pipeline before and after March.",
            xKey: "month",
            yKey: "revenue",
            data
          },
          sources,
          bullets: [
            "Delayed onboarding moved recognition into April.",
            "Procurement and security reviews postponed expansion billing.",
            "Pipeline stayed healthy, indicating timing pressure rather than broad contraction."
          ]
        }
      ]
    },
    queryTrace: [
      trace("sql", "Revenue around March", MARCH_REVENUE_SQL, revenueResult),
      trace("hybrid", "March evidence via Oracle Text and vectors", MARCH_HYBRID_SQL, evidenceResult)
    ]
  };
}

export async function runDataChat(message: string, options: RunDataChatOptions = {}): Promise<DataChatApiResponse> {
  assertNotAborted(options.signal);
  report(options, {
    phase: "model",
    message: "Planning the Oracle retrieval path",
    detail: "The model selects one supported intent and a typed UI shape; it cannot submit arbitrary SQL."
  });
  const plan = await createPlan(message, options.signal);

  report(options, {
    phase: "oracle",
    message: `Running the ${plan.strategy.toUpperCase()} strategy`,
    detail: "The server maps the validated plan to predefined SQL, vector, or hybrid statements."
  });

  let result: DataChatApiResponse;
  switch (plan.intent) {
    case "revenueTrend":
      result = await revenueAnswer(plan, options.signal);
      break;
    case "topAccounts":
      result = await topAccountsAnswer(plan, options.signal);
      break;
    case "activeUsers":
      result = await activeUsersAnswer(plan, options.signal);
      break;
    case "contractSearch":
      result = await contractSearchAnswer(plan, options.signal);
      break;
    case "marchDip":
      result = await marchDipAnswer(plan, options.signal);
      break;
  }

  assertNotAborted(options.signal);
  report(options, {
    phase: "render",
    message: "Validating the generated interface",
    detail: "Zod validates every component and execution trace before the response reaches React."
  });
  return DataChatApiResponseSchema.parse(result);
}
