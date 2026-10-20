<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0 (MINOR: expanded guidance; no principle removed or renamed)
- Modified principles:
  - I. Database-Native Intelligence: indexing stated to have no exceptions; added one opt-in
    exception for agent-memory distillation, with an optional, documented model and per-fact
    provenance
- Added sections: none
- Removed sections: none
- Reason: feature 010-agent-memory uses Oracle's AI Agent Memory package in full, including
  its language-model extraction (user decision, 2026-10-12)
- Migration: specs/010-agent-memory plan and spec must be updated to the exception's rules;
  earlier specs are unaffected (they send nothing out)
- Templates: none modified (dependent templates read this file at runtime)
- Deferred TODOs: none
-->

# Code Context MCP Server Constitution

A searchable, self-improving brain for codebases that any AI coding tool can plug into: it
ingests one or many repositories into a database, chunks them at function and class boundaries,
answers plain-English questions over them, and serves everything over the Model Context Protocol.

## Core Principles

### I. Database-Native Intelligence

- Embedding generation, hybrid (keyword + semantic) search, and code-relationship (graph)
  queries MUST run inside the database engine. The reference stack is Oracle AI Database 26ai.
- Source code MUST NOT be sent to an external service to be indexed, and the core feature set
  MUST work without any third-party embedding API key. Indexing (chunking, embeddings, search,
  graph) has no exceptions.
- One exception applies to agent-memory distillation: it MAY send tool-call results, including
  code snippets and symbol source, to a language model the operator explicitly configures.
  - The model MUST be optional. With none configured, memory MUST still record, consolidate
    (with a local distiller that sends nothing out) and recall. No core feature may need a
    third-party API key.
  - The configured model and exactly what is sent to it MUST be documented.
  - Every distilled fact MUST record whether a model wrote it, and which one.
- An alternative stack is permitted only if a plan documents how it meets the same guarantees;
  each extra piece of infrastructure MUST be justified in the plan's Complexity Tracking.

Rationale: one engine for vectors, text, and graph keeps code private, removes API-key
setup, and avoids synchronizing three or four separate stores. Memory distillation is the one
place where a model's reading of the code is worth sending it out. It is opt-in, it is
recorded on every fact it touches, and it is never needed to find code.

### II. Structure-Aware Ingestion

- Code MUST be chunked at syntactic boundaries (functions, methods, classes, modules) using a
  real parser, never by fixed character or line windows alone. Fallback windowing is allowed
  only for unsupported languages and MUST be flagged on the chunk.
- Every chunk MUST carry repository, file path, language, symbol name, kind, line range, and a
  content hash.
- Re-ingestion MUST be incremental and idempotent: unchanged content (same hash) is not
  re-embedded, and deleted or changed code removes or invalidates its stale chunks and edges.
- Multiple codebases MUST be indexable side by side and filterable by repository.

Rationale: answers are only as good as the units they are built from; function-level units
give precise citations and meaningful call/containment relationships.

### III. MCP as the Single Interface

- All capabilities (search, symbol lookup, relationship queries, notes, feedback) MUST be
  exposed as MCP tools/resources usable by any compliant client (Claude Code, Codex, Cursor,
  etc.). No client-specific behavior.
- Tool names, input schemas, and output shapes are a public contract: breaking changes require
  a MAJOR version bump of the server and a documented migration.
- Every tool result MUST be structured, bounded in size, and include source locations
  (repo, path, line range) so the client can open the code directly.
- A CLI MAY exist for ingestion and administration, but it MUST call the same core library as
  the MCP server.

Rationale: the value is a shared brain; one interface means every tool sees the same context.

### IV. Hybrid, Explainable Retrieval

- Default search MUST fuse keyword and semantic results (e.g., reciprocal rank fusion) and MAY
  add graph proximity and learned feedback signals.
- Each returned result MUST expose why it ranked: component scores (keyword, semantic, graph,
  feedback) or an equivalent explanation.
- Ranking weights MUST be configurable and MUST have documented defaults.

Rationale: neither keyword nor vector search alone handles both exact identifiers and vague
natural-language questions; explainable scores make tuning and trust possible.

### V. Self-Improvement with Provenance

- The server MUST let agents write and retrieve notes (learned facts, summaries, decisions)
  linked to the code they describe, and these notes MUST be searchable alongside code.
- Every note MUST record its author (agent/client or human), creation time, and the content
  hashes of the code it references; notes whose referenced code changed MUST be marked stale
  rather than silently served as current.
- Usage feedback (which results were actually used or rated helpful) MUST be recorded and MAY
  influence ranking; its influence MUST be bounded, decay over time, and be resettable.
- Learned state MUST never overwrite or alter indexed source content.

Rationale: the brain improves only if what it learns is attributable, invalidated when the
code moves on, and unable to drown out ground truth.

### VI. Measured Quality (Test-First)

- Tests MUST be written before or alongside implementation and MUST fail before the code
  that satisfies them is written.
- Each MCP tool MUST have a contract test; ingestion, chunking, and ranking MUST have
  integration tests against a real (containerized or local) database instance.
- Retrieval quality MUST be tracked with a versioned evaluation set of question → expected
  location pairs (e.g., top-5 hit rate); a change that lowers the tracked metric MUST be
  justified in its review.

Rationale: "it seems to find things" is not a quality bar; retrieval regressions are invisible
without a fixed benchmark.

### VII. Safety & Simplicity

- Indexing is read-only with respect to the target codebases: the server MUST NOT execute,
  modify, or import indexed code.
- Ingestion MUST honor ignore rules (.gitignore plus a configurable denylist) and MUST skip
  likely secrets (key files, .env, credentials) and binaries by default.
- Database credentials MUST come from environment or a secrets store, never from source.
- Start with the simplest design that satisfies the spec (YAGNI). No abstraction layer with a
  single implementation, no speculative plugin system; added complexity MUST be justified in
  the plan's Complexity Tracking.

Rationale: a tool that reads every file in a repo must be trustworthy by default, and a small
codebase is easier to verify than a clever one.

## Technology & Data Constraints

- Reference database: Oracle AI Database 26ai (in-database ONNX embedding model, vector index,
  Oracle Text, and SQL/property-graph queries). Local development MUST be reproducible with a
  documented container or free-tier setup.
- The embedding model and its dimension MUST be recorded per index; changing the model
  requires a full re-embed and MUST NOT mix vectors from different models in one index.
- Schema changes MUST ship as ordered, re-runnable migrations.
- Structured logging MUST cover ingestion runs (files seen, chunks added/updated/removed,
  duration, errors) and tool calls (tool, latency, result count), without logging source bodies
  or secrets.
- Performance targets are set per feature in the spec; plans MUST state how they will be
  verified.

## Development Workflow & Quality Gates

- Work follows the Spec Kit flow: specify → (clarify) → plan → tasks → implement. Every plan
  MUST include a Constitution Check against Principles I–VII before and after design.
- A change merges only when: tests pass, contract tests cover every changed MCP tool, the
  retrieval evaluation has been run if ranking/chunking/embedding changed, and documentation
  of any tool contract change is updated.
- Reviews MUST reject: source code sent off-database for indexing, chunking that ignores
  syntax for supported languages, tool results without source locations, and notes or
  feedback without provenance.

## Governance

- This constitution supersedes other practices and guidance in this repository. Conflicts are
  resolved in favor of the constitution until it is amended.
- Amendments are made through `/speckit-constitution`, MUST include a Sync Impact Report, and
  MUST state the reason for change and any migration needed for in-flight specs or plans.
- Versioning follows semantic versioning: MAJOR for removing or redefining a principle,
  MINOR for adding a principle or section or materially expanding guidance, PATCH for
  clarifications and wording.
- Compliance is reviewed at every plan's Constitution Check and at code review; justified
  deviations MUST be recorded in the plan's Complexity Tracking table.

**Version**: 1.1.0 | **Ratified**: 2026-10-10 | **Last Amended**: 2026-10-12
