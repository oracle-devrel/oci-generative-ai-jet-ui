"""Unmodified synthetic research corpus from Hybrid Retrieval."""
DOCUMENTS = [
    # -- the two documents Jane names ----------------------------------------
    ("ingested-papers", "letta", "Letta: Agent Memory Beyond the Context Window",
     "https://arxiv.org/abs/2310.08560", "pdf"),
    ("vendor-docs", "agentcore", "Amazon Bedrock AgentCore Memory Developer Guide",
     "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html", "html"),

    # -- hard negatives: same subject matter, different source ---------------
    ("ingested-papers", "memgpt", "MemGPT: Towards LLMs as Operating Systems",
     "https://arxiv.org/abs/2310.08560", "pdf"),
    ("ingested-papers", "ctxmgmt", "Context Window Management in Long-Running Agents",
     "https://example.org/papers/context-window-management", "pdf"),
    ("ingested-papers", "summarization", "Conversation Summarization Techniques for Dialogue Agents",
     "https://example.org/papers/conversation-summarization", "pdf"),
    ("ingested-papers", "longterm", "Scalable Long-Term Memory for Conversational Agents",
     "https://example.org/papers/scalable-long-term-memory", "pdf"),
    ("ingested-papers", "longctx", "Sliding Window Attention and Long-Context Transformers",
     "https://example.org/papers/long-context-transformers", "pdf"),
    ("ingested-papers", "episodic", "Episodic Memory for Embodied and Situated Agents",
     "https://example.org/papers/episodic-memory-agents", "pdf"),
    ("ingested-papers", "ragdialog", "Retrieval-Augmented Dialogue Systems",
     "https://example.org/papers/retrieval-augmented-dialogue", "pdf"),
    ("ingested-papers", "forgetting", "Forgetting Mechanisms in Neural Memory Systems",
     "https://example.org/papers/forgetting-mechanisms", "pdf"),

    # -- retrieval / evaluation literature -----------------------------------
    ("ingested-papers", "ragsurvey", "A Survey of Retrieval-Augmented Generation for Large Language Models",
     "https://arxiv.org/abs/2312.10997", "pdf"),
    ("ingested-papers", "dpr", "Dense Passage Retrieval for Open-Domain Question Answering",
     "https://arxiv.org/abs/2004.04906", "pdf"),
    ("ingested-papers", "bm25", "BM25 and Lexical Retrieval Revisited",
     "https://example.org/papers/bm25-revisited", "pdf"),
    ("ingested-papers", "reranking", "Cross-Encoder Reranking for Passage Ranking",
     "https://example.org/papers/cross-encoder-reranking", "pdf"),
    ("ingested-papers", "evalmetrics", "Evaluating Retrieval: NDCG, MRR, and Recall",
     "https://example.org/papers/evaluating-retrieval", "pdf"),
    ("ingested-papers", "chunking", "Chunking Strategies for Retrieval-Augmented Generation",
     "https://example.org/papers/chunking-strategies", "pdf"),
    ("ingested-papers", "hyde", "Query Expansion and Hypothetical Document Embeddings",
     "https://example.org/papers/query-expansion-hyde", "pdf"),

    # -- vendor documentation -------------------------------------------------
    ("vendor-docs", "langgraph", "LangGraph Checkpointing and Persistence Guide",
     "https://langchain-ai.github.io/langgraph/concepts/persistence/", "html"),
    ("vendor-docs", "oraclevs", "Oracle AI Vector Search Developer Guide",
     "https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/", "html"),
    ("vendor-docs", "vectortuning", "Vector Index Tuning Guide",
     "https://example.org/docs/vector-index-tuning", "html"),
    ("vendor-docs", "sessionstate", "In-Memory Session State for LLM Applications",
     "https://example.org/docs/session-state", "html"),
    ("vendor-docs", "metadatafilter", "Namespace and Metadata Filtering Reference",
     "https://example.org/docs/metadata-filtering", "html"),
    ("vendor-docs", "multitenant", "Multi-Tenant Data Isolation Patterns",
     "https://example.org/docs/multi-tenant-isolation", "html"),
]

CHUNKS = [
    # ======================= LETTA (the paper Jane names) ====================
    ("letta", "abstract",
     "Letta is an agent framework that treats the context window as a managed resource "
     "rather than a fixed budget. It descends from the MemGPT line of work, which framed "
     "the language model as an operating system kernel paging information between a small "
     "fast tier and a large slow tier."),
    ("letta", "introduction",
     "An agent that runs for weeks accumulates far more conversation than any context "
     "window can hold. Naive truncation drops the oldest turns and with them the reasons "
     "behind earlier decisions, so the agent contradicts itself over long horizons."),
    ("letta", "introduction",
     "The contribution is a memory hierarchy the model administers itself. Rather than an "
     "external process deciding what the agent remembers, the agent issues function calls "
     "to read and write its own memory tiers."),

    # --- the chunk that actually answers Jane's question --------------------
    ("letta", "memory-management",
     "Letta frames eviction as recursive summarization. When the working context approaches "
     "its limit, the oldest span of messages is compressed into a summary that is written "
     "back into archival memory, and the raw messages are evicted from the window. The "
     "summary is itself eligible for later compression, so the process is recursive: "
     "summaries of summaries preserve a decaying trace of the entire history."),

    # --- near-duplicates: what crowds the top of a vector-only candidate list
    ("letta", "memory-management",
     "Eviction in Letta is driven by a pressure signal on the working context. As the "
     "context fills, the manager selects the oldest message span, produces a compressed "
     "summary of it, and removes the original messages from the window. Because summaries "
     "can themselves be summarized, the scheme degrades gracefully over long sessions."),
    ("letta", "memory-management",
     "The memory manager evicts messages under context pressure. A span of older turns is "
     "replaced by a generated summary, which is persisted to archival storage while the raw "
     "turns leave the working set. Repeated application yields recursive summarization, the "
     "mechanism Letta relies on for unbounded conversations."),
    ("letta", "memory-management",
     "Context pruning proceeds by recursive summarization: the oldest messages are distilled "
     "into a compact summary, the originals are evicted, and the summary re-enters the window "
     "in their place. Subsequent rounds may compress that summary again."),
    ("letta", "memory-management",
     "When the token count crosses a configured threshold, Letta triggers a flush. The flush "
     "summarizes and evicts the oldest portion of the message buffer, freeing room while "
     "retaining a lossy record of what was removed."),

    ("letta", "architecture",
     "Memory in Letta is tiered. Main context holds the system prompt, a working set of "
     "recent messages, and a small editable scratchpad. External context holds archival "
     "storage and a recall database, both reachable through function calls."),
    ("letta", "architecture",
     "Memory blocks are named, size-bounded regions of the prompt the agent can rewrite. A "
     "persona block and a human block are conventional, and additional blocks can be defined "
     "per deployment."),
    ("letta", "architecture",
     "Archival memory is an append-mostly vector store the agent searches by similarity. "
     "Recall memory indexes the full message history so specific past turns can be retrieved "
     "verbatim rather than through a summary."),
    ("letta", "evaluation",
     "The paper evaluates on multi-session dialogue and document question answering, "
     "reporting that tiered memory with recursive summarization sustains coherence across "
     "sessions far longer than a fixed truncation baseline."),
    ("letta", "evaluation",
     "Ablations remove the recursive step and summarize only once. Coherence degrades sharply "
     "on the longest sessions, which the authors attribute to unbounded growth of the single "
     "summary rather than to information loss per se."),
    ("letta", "discussion",
     "A limitation is that summarization is lossy in ways the agent cannot detect. Once a "
     "detail is compressed away it is unrecoverable from the window, and the agent has no "
     "signal that it is reasoning over a lossy trace."),

    # --- the references chunk: matches "Letta" repeatedly, answers nothing ---
    ("letta", "references",
     "References. Packer et al. Letta and MemGPT: Towards LLMs as Operating Systems. See also "
     "the Letta documentation, the Letta framework repository, the Letta agent development "
     "guide, the Letta memory blocks reference, Letta deployment notes, and subsequent Letta "
     "papers on agent state. Letta, Letta, Letta."),

    # ======================= AGENTCORE (the vendor docs) =====================
    ("agentcore", "overview",
     "Amazon Bedrock AgentCore Memory gives agents both short-term and long-term memory. "
     "Short-term memory holds the raw events of a session; long-term memory holds durable "
     "records extracted from those events by configurable strategies."),
    ("agentcore", "overview",
     "A memory resource is the top-level container. Creating one establishes the namespaces, "
     "the extraction strategies, and the retention configuration that govern everything "
     "written beneath it."),

    # --- the chunk that answers the AgentCore half of the question ----------
    # Deliberately written in AWS's own vocabulary: expiry, retention, extraction
    # strategies. It never says "eviction", "pruning" or "summarizing under pressure",
    # because the real documentation doesn't. This is the vocabulary gap the article is
    # about -- a vendor describing the same lifecycle concern in entirely different words.
    # Phrasing this chunk in the questioner's terms would make it trivially findable and
    # would quietly turn the whole evaluation into a tautology.
    ("agentcore", "retention",
     "Each memory resource defines an event expiry period, specified in days. When that "
     "period lapses the raw session events are removed automatically. Records that the "
     "extraction strategies have already promoted into long-term memory are unaffected, so "
     "configuring strategies is how you determine what outlives a session."),

    ("agentcore", "retention",
     "Retention is configured per memory resource rather than per session. The setting "
     "governs the short-term event stream only; long-term records persist independently of "
     "the events they were derived from."),
    ("agentcore", "strategies",
     "Built-in extraction strategies cover semantic facts, user preferences, and session "
     "summaries. A custom strategy can override the prompt used for extraction."),
    ("agentcore", "strategies",
     "Strategies run asynchronously after events are written, so long-term memory is "
     "eventually consistent with the session. An application that reads immediately after "
     "writing may not see extracted records yet."),
    ("agentcore", "namespaces",
     "Long-term memories are organized by namespace, which scopes a record to an actor, a "
     "session, or a broader grouping. Retrieval takes a namespace and a query string and "
     "returns semantically matching records."),
    ("agentcore", "namespaces",
     "Namespace templates interpolate identifiers such as actor and session, so a single "
     "strategy definition can partition memories per user without enumerating them."),
    ("agentcore", "short-term",
     "Short-term memory is retrieved as the recent turns of a session, in order, and is "
     "intended to be passed to the model directly as conversational context."),
    ("agentcore", "short-term",
     "Events are appended with an actor identifier and a role. The service does not "
     "summarize or compress the event stream; it stores what the application writes until "
     "expiry."),
    ("agentcore", "integration",
     "The memory APIs are independent of the agent runtime, so an agent hosted elsewhere can "
     "still use AgentCore Memory by calling the create-event and retrieve-memory operations "
     "directly."),

    # ======================= MEMGPT (closest hard negative) ==================
    ("memgpt", "abstract",
     "MemGPT introduces a virtual context management scheme inspired by operating system "
     "paging. The model moves information between an in-context working set and out-of-context "
     "storage through explicit function calls it decides to issue."),
    ("memgpt", "introduction",
     "Fixed context windows are the binding constraint on conversational agents. Rather than "
     "enlarging the window, MemGPT treats it as physical memory and adds a paging layer."),
    ("memgpt", "memory-management",
     "When the context window fills, MemGPT flushes older messages to external storage after "
     "generating a recursive summary, keeping a pointer so the detail can be paged back in "
     "on demand."),
    ("memgpt", "memory-management",
     "A memory pressure warning is injected into the context when utilization crosses a "
     "threshold, prompting the model to take an eviction action before it is forced."),
    ("memgpt", "architecture",
     "Main context is divided into system instructions, working context, and the FIFO message "
     "queue. External context comprises recall storage and archival storage."),
    ("memgpt", "evaluation",
     "Evaluation covers deep memory retrieval and nested key-value lookup, showing that paged "
     "virtual context outperforms a fixed window on tasks requiring old information."),
    ("memgpt", "discussion",
     "The authors note that function-calling reliability bounds the approach: an agent that "
     "fails to issue a paging call at the right moment loses the information regardless of "
     "what storage holds."),

    # ======================= CONTEXT WINDOW MANAGEMENT =======================
    ("ctxmgmt", "abstract",
     "Long-running agents must decide continuously what to keep in the context window. This "
     "survey compares truncation, summarization, retrieval, and hybrid schemes across several "
     "open agent frameworks."),
    ("ctxmgmt", "methods",
     "Sliding-window truncation is the cheapest policy and the most lossy. Summarization "
     "trades compute for retention. Retrieval-based schemes keep the window small and pull "
     "detail back on demand, at the cost of a retrieval failure mode."),
    ("ctxmgmt", "methods",
     "Hybrid policies summarize the middle of a session while preserving the first and last "
     "turns verbatim, on the observation that openings carry task framing and recent turns "
     "carry active state."),
    ("ctxmgmt", "methods",
     "Eviction policies borrowed from cache design — least recently used, least frequently "
     "referenced — have been applied to message spans, with mixed results because relevance "
     "in dialogue is not well predicted by recency alone."),
    ("ctxmgmt", "evaluation",
     "The authors measure coherence over synthetic 200-turn sessions, scoring whether the "
     "agent contradicts commitments it made earlier."),
    ("ctxmgmt", "discussion",
     "No single policy dominates. Agents with bounded sessions do well with truncation; agents "
     "with open-ended relationships to a user need durable memory outside the window."),
    ("ctxmgmt", "discussion",
     "The survey argues that context management and retrieval are the same problem viewed "
     "from two directions, and that treating them separately produces systems that summarize "
     "away exactly what retrieval would later need."),

    # ======================= SUMMARIZATION ===================================
    ("summarization", "abstract",
     "Dialogue summarization condenses conversational history while preserving entities, "
     "commitments, and unresolved threads. Abstractive methods generate new text; extractive "
     "methods select salient turns."),
    ("summarization", "methods",
     "Hierarchical summarization compresses in stages, summarizing summaries as a session "
     "grows. Fidelity degrades with each stage, so entity anchoring is commonly used to "
     "preserve names and numbers through successive rounds."),
    ("summarization", "methods",
     "Incremental summarization updates a running summary after each turn rather than "
     "recomputing from the full history, trading fidelity for bounded cost per turn."),
    ("summarization", "evaluation",
     "Reference-based metrics correlate poorly with downstream task success, so the paper "
     "advocates measuring whether the summary preserves the information a later question "
     "actually needs."),
    ("summarization", "discussion",
     "Compression is not lossless and the loss is not uniform: numbers, negations, and "
     "conditionals are dropped disproportionately relative to their importance."),

    # ======================= LONG-TERM MEMORY ================================
    ("longterm", "abstract",
     "This work proposes a memory layer that extracts durable facts from conversation and "
     "stores them independently of the session, so an agent can recall a user's preferences "
     "across unrelated sessions."),
    ("longterm", "methods",
     "Extraction runs asynchronously over completed turns, producing candidate facts that are "
     "deduplicated against existing memory before being written."),
    ("longterm", "methods",
     "Conflicting facts are resolved by recency with a confidence weight, and superseded "
     "facts are retained with a validity interval rather than deleted."),
    ("longterm", "methods",
     "Retrieval is a similarity search over the fact store, filtered by the user the facts "
     "belong to. The paper stresses that the filter is a correctness requirement, not an "
     "optimization."),
    ("longterm", "evaluation",
     "On a multi-session benchmark the memory layer improves answer accuracy on questions "
     "whose evidence appeared in an earlier session."),
    ("longterm", "discussion",
     "The authors observe that extraction quality, not storage or retrieval, is the binding "
     "constraint: facts never extracted cannot be recalled no matter how good the index is."),

    # ======================= LONG CONTEXT ====================================
    ("longctx", "abstract",
     "Sliding window attention bounds the quadratic cost of self-attention by restricting "
     "each token's receptive field, enabling far longer sequences at a fixed compute budget."),
    ("longctx", "methods",
     "Dilated and global-token variants restore some long-range connectivity by letting a "
     "small number of positions attend everywhere."),
    ("longctx", "evaluation",
     "Retrieval accuracy within very long contexts is uneven: models attend strongly to the "
     "beginning and end of the window and weakly to the middle."),
    ("longctx", "discussion",
     "A larger window does not remove the need to choose what goes in it. Degraded attention "
     "in the middle of long contexts means ordering still determines what the model uses."),
    ("longctx", "discussion",
     "The paper cautions against reading long-context benchmarks as evidence that retrieval "
     "is unnecessary, since benchmark passages are typically placed adversarially rather than "
     "assembled from a noisy corpus."),

    # ======================= EPISODIC MEMORY =================================
    ("episodic", "abstract",
     "Episodic memory stores specific past experiences with their temporal and situational "
     "context, in contrast to semantic memory which stores decontextualized facts."),
    ("episodic", "methods",
     "Episodes are segmented at boundaries detected from changes in task or location, then "
     "indexed by embedding along with their timestamps."),
    ("episodic", "methods",
     "Consolidation periodically promotes recurring patterns from episodic traces into "
     "semantic memory, a process loosely modeled on sleep-dependent consolidation."),
    ("episodic", "evaluation",
     "Agents with episodic recall outperform flat-memory baselines on tasks requiring the "
     "agent to remember how a similar situation was handled previously."),
    ("episodic", "discussion",
     "Unbounded episodic growth forces a forgetting policy, and the authors note that the "
     "choice of what to forget is effectively a choice about what the agent can become."),

    # ======================= RETRIEVAL-AUGMENTED DIALOGUE ====================
    ("ragdialog", "abstract",
     "Retrieval-augmented dialogue grounds each response in passages fetched at turn time, "
     "reducing hallucination relative to closed-book generation."),
    ("ragdialog", "methods",
     "Query construction is the hard part in dialogue: the user's latest turn is often "
     "elliptical, so the retrieval query must be rewritten using conversational context."),
    ("ragdialog", "methods",
     "Rewriting can be learned or prompted. Prompted rewriting with a small fast model is "
     "the common production choice because it adds a bounded, predictable latency."),
    ("ragdialog", "evaluation",
     "Groundedness improves with retrieval quality but saturates: beyond a point, adding "
     "passages dilutes the prompt and accuracy falls."),
    ("ragdialog", "discussion",
     "The authors argue that dialogue systems should retrieve from their own conversation "
     "history as well as from a document corpus, treating both as one ranked pool."),

    # ======================= FORGETTING ======================================
    ("forgetting", "abstract",
     "Forgetting is treated here as a design parameter rather than a failure. A memory system "
     "that never forgets accumulates stale and contradictory content that degrades retrieval."),
    ("forgetting", "methods",
     "Decay functions age memories by time since last access, so frequently used memories "
     "persist and unused ones fall below a retention threshold."),
    ("forgetting", "methods",
     "Explicit invalidation marks a memory superseded when a contradicting fact arrives, "
     "preserving the old value with a closed validity interval for audit."),
    ("forgetting", "evaluation",
     "Aggressive forgetting improves precision and harms recall; the paper reports the "
     "trade-off curve across several decay rates."),
    ("forgetting", "discussion",
     "The authors distinguish eviction from a working buffer, which is about capacity, from "
     "forgetting in durable storage, which is about correctness. Conflating the two produces "
     "systems that delete durable facts for capacity reasons."),

    # ======================= RAG SURVEY ======================================
    ("ragsurvey", "abstract",
     "Retrieval-augmented generation grounds model output in retrieved passages. This survey "
     "organizes the literature into naive, advanced, and modular RAG paradigms."),
    ("ragsurvey", "retrieval",
     "Advanced RAG adds pre-retrieval query rewriting and post-retrieval reranking. Reranking "
     "with a cross-encoder consistently improves ordering over bi-encoder similarity alone."),
    ("ragsurvey", "retrieval",
     "Hybrid retrieval combining sparse and dense signals outperforms either alone on "
     "heterogeneous corpora, particularly where rare identifiers matter."),
    ("ragsurvey", "retrieval",
     "Fusion methods range from score normalization to rank-based combination. Rank-based "
     "fusion avoids the calibration problem entirely and is difficult to beat without "
     "corpus-specific tuning."),
    ("ragsurvey", "evaluation",
     "Common metrics are recall at k for the retriever and faithfulness or answer relevance "
     "for the generator. The survey notes that retrieval quality bounds end-to-end quality."),
    ("ragsurvey", "discussion",
     "Modular RAG decomposes the pipeline into interchangeable stages, which the survey "
     "argues is a prerequisite for measuring any single stage's contribution."),

    # ======================= DPR =============================================
    ("dpr", "abstract",
     "Dense passage retrieval learns a bi-encoder that maps questions and passages into a "
     "shared space, retrieving by inner product rather than lexical overlap."),
    ("dpr", "methods",
     "Training uses in-batch negatives plus mined hard negatives, which the paper finds "
     "essential: without hard negatives the encoder learns only coarse topical similarity."),
    ("dpr", "methods",
     "Question and passage encoders are separate towers, so passage embeddings can be "
     "precomputed and indexed offline. This is what makes the approach scalable."),
    ("dpr", "evaluation",
     "Dense retrieval beats BM25 on natural-language questions but underperforms on queries "
     "dominated by rare entities or exact strings."),
    ("dpr", "discussion",
     "The independence of the two towers is both the source of scalability and the ceiling "
     "on precision, since neither text is encoded with knowledge of the other."),

    # ======================= BM25 ============================================
    ("bm25", "abstract",
     "BM25 remains a strong baseline for retrieval, particularly where queries contain exact "
     "identifiers, code fragments, or error strings."),
    ("bm25", "methods",
     "The scoring function weights term frequency with saturation and penalizes long "
     "documents, with two parameters controlling each effect."),
    ("bm25", "methods",
     "Lexical retrieval fails when the query and document use different vocabulary for the "
     "same concept, a mismatch no amount of parameter tuning repairs."),
    ("bm25", "evaluation",
     "On benchmarks with heavy entity overlap between query and document, BM25 matches or "
     "exceeds dense retrievers trained on far more data."),
    ("bm25", "discussion",
     "The paper argues that lexical and dense retrieval fail on disjoint query populations, "
     "which is the case for combining them rather than choosing between them."),

    # ======================= RERANKING =======================================
    ("reranking", "abstract",
     "Cross-encoder reranking scores a query and a candidate jointly in a single forward "
     "pass, producing a relevance estimate computed with full knowledge of both texts."),
    ("reranking", "methods",
     "Because scoring is per pair, cross-encoders cannot precompute document representations "
     "and cannot be used to search a corpus. They operate only on a candidate set produced "
     "by something cheaper."),
    ("reranking", "methods",
     "Candidate set size controls the quality-latency trade-off. A larger set gives the "
     "reranker more chances to recover a good passage the retriever ranked poorly, at linear "
     "cost in inference time."),
    ("reranking", "evaluation",
     "Reranking improves ordering metrics substantially while leaving recall unchanged, since "
     "it only reorders what it was given."),
    ("reranking", "discussion",
     "The authors note that reranking cannot repair a candidate set that omits the answer, "
     "making retriever recall the binding constraint on the pipeline."),

    # ======================= EVAL METRICS ====================================
    ("evalmetrics", "abstract",
     "This tutorial reviews ranking metrics and the conditions under which each is "
     "informative for retrieval evaluation."),
    ("evalmetrics", "methods",
     "Recall at k measures how many relevant items appear in the top k without regard to "
     "their order, making it the natural metric for a candidate-generation stage."),
    ("evalmetrics", "methods",
     "Normalized discounted cumulative gain rewards placing highly relevant items early, "
     "supports graded relevance, and is the appropriate choice when a downstream consumer "
     "reads results in order."),
    ("evalmetrics", "methods",
     "Mean reciprocal rank considers only the first relevant result and is appropriate when "
     "a single correct answer suffices."),
    ("evalmetrics", "evaluation",
     "Small evaluation sets produce wide confidence intervals; the tutorial recommends "
     "reporting variance and treating differences below it as noise."),
    ("evalmetrics", "discussion",
     "Metric choice should follow how the results are consumed. Optimizing recall when the "
     "consumer reads only the top few is a common and expensive mistake."),

    # ======================= CHUNKING ========================================
    ("chunking", "abstract",
     "Chunk boundaries determine what can be retrieved. This study compares fixed-size, "
     "sentence-aware, and structure-aware chunking across several corpora."),
    ("chunking", "methods",
     "Overlap between adjacent chunks reduces the chance that an answer straddles a boundary, "
     "at the cost of index size and near-duplicate results."),
    ("chunking", "methods",
     "Structure-aware chunking that respects section boundaries preserves the coherence of "
     "each chunk and enables section-level metadata filtering."),
    ("chunking", "evaluation",
     "Retrieval quality is more sensitive to chunk size than to embedding model choice within "
     "the range tested."),
    ("chunking", "discussion",
     "Near-duplicate chunks created by overlap inflate apparent redundancy in results and "
     "should be collapsed after ranking rather than avoided during indexing."),

    # ======================= QUERY EXPANSION =================================
    ("hyde", "abstract",
     "Query expansion rewrites a short query into a richer form before retrieval, closing "
     "part of the vocabulary gap between questions and documents."),
    ("hyde", "methods",
     "Hypothetical document embedding generates a plausible answer and embeds that instead of "
     "the question, on the theory that answers look more like documents than questions do."),
    ("hyde", "methods",
     "Synonym expansion for lexical retrieval adds alternate surface forms for key concepts, "
     "which matters when the corpus uses different terminology than the user."),
    ("hyde", "evaluation",
     "Expansion helps most on short, underspecified queries and can hurt on queries that are "
     "already precise, by diluting the discriminative terms."),
    ("hyde", "discussion",
     "Extracting named entities before expansion and preserving them verbatim protects the "
     "exact-match signal that expansion would otherwise wash out."),

    # ======================= LANGGRAPH =======================================
    ("langgraph", "overview",
     "Checkpointing persists graph state after each node, so a run can be resumed, inspected, "
     "or replayed from any prior step."),
    ("langgraph", "methods",
     "A checkpointer writes state to a backing store keyed by thread. Threads isolate "
     "concurrent conversations from one another."),
    ("langgraph", "methods",
     "State is a typed dictionary whose keys are updated by nodes; reducers control how "
     "concurrent updates to the same key are merged."),
    ("langgraph", "methods",
     "Interrupting before or after a node enables human-in-the-loop review, with the run "
     "resuming from the persisted checkpoint once approved."),
    ("langgraph", "discussion",
     "Persistence at the orchestration layer is distinct from the agent's memory: one records "
     "how the run progressed, the other records what the agent knows."),

    # ======================= ORACLE VECTOR SEARCH ============================
    ("oraclevs", "overview",
     "AI Vector Search adds a native VECTOR data type and distance operators, so similarity "
     "search runs inside SQL alongside relational predicates and joins."),
    ("oraclevs", "methods",
     "VECTOR_EMBEDDING generates an embedding inside the database from a loaded ONNX model, "
     "so query text never leaves the engine to be vectorized."),
    ("oraclevs", "methods",
     "In-memory neighbor graph indexes provide approximate search with a configurable target "
     "accuracy, trading recall against query time."),
    ("oraclevs", "methods",
     "Because vector predicates compose with ordinary SQL predicates, the optimizer chooses "
     "whether to filter before or after the index probe based on statistics."),
    ("oraclevs", "methods",
     "Hybrid search combining vector distance with an Oracle Text CONTAINS score can be "
     "expressed in a single statement, with both pools reading one transactional snapshot."),
    ("oraclevs", "discussion",
     "Keeping retrieval in the database means security policies, snapshots, and query planning "
     "apply to it automatically rather than being reimplemented in application code."),

    # ======================= VECTOR TUNING ===================================
    ("vectortuning", "overview",
     "Vector index tuning balances recall against latency and memory. Graph indexes expose a "
     "target accuracy parameter that governs how much of the graph is explored per query."),
    ("vectortuning", "parameters",
     "Raising target accuracy increases the number of neighbors visited, improving recall at "
     "the cost of query time."),
    ("vectortuning", "parameters",
     "Memory sizing determines whether the graph stays resident. An undersized pool forces "
     "index build failures or falls back to exact search."),
    ("vectortuning", "parameters",
     "Rebuilding is required after a change of embedding model, since the vector space itself "
     "changes and prior neighbors are no longer meaningful."),
    ("vectortuning", "discussion",
     "Accuracy targets should be validated against a labeled set rather than accepted from "
     "defaults, because achievable recall depends on the distribution of the data."),

    # ======================= SESSION STATE ===================================
    ("sessionstate", "overview",
     "In-memory stores are commonly used to hold the active turn buffer for a conversation, "
     "where low latency matters more than durability."),
    ("sessionstate", "methods",
     "Time-to-live on session keys bounds memory growth, with the practical consequence that "
     "anything not promoted to durable storage before expiry is lost."),
    ("sessionstate", "methods",
     "Separating the volatile turn buffer from durable memory avoids the mistake of treating "
     "a cache eviction as a decision about what the agent should remember."),
    ("sessionstate", "discussion",
     "The guide recommends writing durable facts synchronously with the turn that produced "
     "them rather than relying on a background job that may not run before expiry."),

    # ======================= METADATA FILTERING ==============================
    ("metadatafilter", "overview",
     "Metadata filters restrict a similarity search to records matching structured criteria, "
     "applied alongside the vector comparison."),
    ("metadatafilter", "methods",
     "Namespaces partition an index so queries never see records outside the requested "
     "partition, which is the usual mechanism for per-tenant separation."),
    ("metadatafilter", "methods",
     "Filter selectivity affects performance: a highly selective filter applied after an "
     "approximate search can leave too few results, so pre-filtering is preferred where "
     "supported."),
    ("metadatafilter", "discussion",
     "A filter expressed in application code is a filter that can be omitted. Enforcing "
     "partitioning in the store removes that class of mistake."),

    # ======================= MULTI-TENANCY ===================================
    ("multitenant", "overview",
     "Multi-tenant systems must guarantee that one tenant's queries can never return another "
     "tenant's rows, regardless of application behavior."),
    ("multitenant", "methods",
     "Shared-table designs with a tenant column are efficient but rely on every query "
     "carrying the predicate, unless the database enforces it."),
    ("multitenant", "methods",
     "Row-level security attaches the predicate at the engine, so it applies to every "
     "reference of the table including joins and subqueries."),
    ("multitenant", "methods",
     "Session context supplies the tenant identity, and the policy function reads it, which "
     "keeps the boundary out of application SQL entirely."),
    ("multitenant", "discussion",
     "Isolation enforced structurally is auditable in a way that isolation enforced by "
     "convention is not: there is one place to inspect rather than every query in the "
     "codebase."),
]
