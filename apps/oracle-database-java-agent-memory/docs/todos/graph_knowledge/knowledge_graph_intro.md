# Knowledge graph memory for RAG agents on Oracle 23ai

**Graph memory transforms RAG from approximate semantic matching into structured, multi-hop reasoning.** For an Oracle Database agent already using JDBC chat history, hybrid vector search, and Spring AI `@Tool` annotations, adding a knowledge graph layer fills the critical gap between "finding similar text" and "reasoning over connected facts." Research consistently shows **10–40+ percentage point improvements on multi-hop queries** when graph augments vector retrieval, while pure vector RAG remains superior for fuzzy semantic search. Oracle 23ai's SQL/PGQ standard — the first commercial implementation of SQL:2023 Part 16 — uniquely enables graph, vector, and relational queries within a single ACID-transactional database, eliminating the need for separate Neo4j or FalkorDB deployments.

---

## 1. Three memory types and how graph memory differs

Knowledge graph memory encodes agent knowledge as **entities (nodes) connected by explicit, typed relationships (edges)**, enabling traversal across connected facts rather than approximate similarity matching. The three memory types in a production agent system serve fundamentally different cognitive roles:

**Episodic memory (chat history)** records raw interaction history — messages, tool outputs, control-flow decisions — preserving temporal ordering and exact conversation context. Your existing JDBC-based `ChatMemory` implementation serves this role. It is analogous to short-term/working memory: a FIFO queue of recent messages, queried by recency or keyword search.

**Semantic memory (vector search)** encodes text fragments as high-dimensional vectors using embedding models and retrieves via approximate nearest neighbor search. Your Oracle Hybrid Vector Index with COSINE distance + Oracle Text keyword search already provides this. Vector memory captures *semantic similarity* — finding passages that "mean similar things" — but loses structural relationships, entity identity, and temporal context. If an agent learns "Alice is vegan" and "Alice is allergic to nuts," vector search treats these as two separate points in embedding space. A knowledge graph stores `(Alice)-[:FOLLOWS_DIET]->(Vegan)` and `(Alice)-[:ALLERGIC_TO]->(TreeNuts)` as traversable, connected facts.

**Structured memory (knowledge graph)** represents knowledge as discrete, typed entities with explicit relationships. Key operations include entity extraction from conversation turns via LLM, relationship modeling as directed labeled edges with properties, and graph traversal for multi-hop retrieval. When a query arrives, the system doesn't just do similarity search — it navigates the graph structure: identify seed entities → traverse adjacent nodes/edges following relationship chains → assemble a subgraph of supporting facts with provenance → pass structured evidence to the LLM for grounded response generation.

### Property graphs vs RDF/SPARQL for agent memory

**Property graphs** (the model used in Oracle 23ai SQL/PGQ, Neo4j, and most GraphRAG implementations) treat relationships as first-class citizens with their own properties. An edge like `WORKS_AT` can carry `start_date`, `role`, and `department` properties directly. Schema is flexible and optional, optimized for real-time traversal and analytics. Query languages include Cypher, GQL (ISO standard, April 2024), and Oracle's PGQL.

**RDF/SPARQL graphs** express everything as subject-predicate-object triples identified by URIs. Edge properties require reification (creating additional triples), making them more verbose. RDF excels at formal ontological reasoning — OWL inference can automatically derive new facts — and cross-system interoperability via W3C standards. However, **for agent memory, property graphs are strongly preferred**: they offer faster traversal, lower learning curve, better tool integration, and native support for edge properties critical to temporal fact management (validity windows, confidence scores, provenance).

| Aspect | Property Graph (SQL/PGQ) | RDF (SPARQL) |
|---|---|---|
| Edge properties | Native, first-class | Requires reification |
| Schema | Flexible, optional | Ontology-driven |
| Reasoning | Custom code/triggers | Built-in OWL inference |
| Traversal speed | Fast, optimized | Slower due to triple volume |
| Agent memory fit | **Recommended** | Only if OWL inference needed |
| Oracle integration | Standard JDBC | SEM_MATCH or Jena adapter |

---

## 2. When graph beats vector and when it doesn't

### Graph memory excels at multi-hop reasoning and entity disambiguation

Graph memory dramatically outperforms vector search for queries requiring reasoning across multiple connected facts. An AWS/Lettria study on legal documents found **graph RAG achieved 80–85% accuracy on complex multi-hop queries vs 45–50% for vector-only RAG** — a 3.2× improvement. On the fast-graphrag benchmark using 2WikiMultiHopQA, graph-based retrieval achieved **96.1% perfect retrieval rate on all questions vs 49.0% for vector DB alone**.

Concrete example: *"Where did the most decorated Olympian of all time get their undergraduate degree?"* requires two retrieval steps — first finding Michael Phelps, then finding his university. Vector search might miss the connection if "most decorated Olympian" isn't close to "University of Michigan" in embedding space. Graph traversal explicitly follows: `Most Decorated Olympian → Michael Phelps → Education → University of Michigan`.

For entity disambiguation, graph memory maintains distinct entity nodes with typed relationships, while vector search struggles when "Apple" could mean the company or the fruit. For temporal reasoning, Zep's temporal knowledge graph achieves **up to 18.5% higher accuracy** over baseline on LongMemEval by tracking both when events occurred and when the system learned about them.

### Vector search remains better for semantic similarity and fuzzy recall

Vector search excels for conceptual, open-ended queries requiring fuzzy matching: "Find documents about climate change impacts on agriculture" works perfectly without entity paths. It's simpler (no schema management, no graph construction pipeline), faster (low-tens-of-milliseconds ANN retrieval from millions of items), and cheaper (graph extraction adds **2–3 extra LLM calls per `add()` operation**). Critically, Amazon/CMU research found that **graph-only RAG was only ~5% better than vector-only RAG** — major gains come from hybrid approaches.

### Hybrid graph+vector architecture delivers the strongest results

The most effective production systems combine both approaches through parallel fan-out retrieval:

```
User Query → Query Analysis (intent + NER + embedding)
    ├── Chat History: Last N messages (always in context)
    ├── Vector Search: Top-K semantically similar facts
    └── Graph Search: Semantic + BM25 + BFS traversal from seed entities
         ↓
    Context Assembly (Reciprocal Rank Fusion + cross-encoder rerank)
         ↓
    LLM Generation (structured context → grounded response)
         ↓
    Async Graph Update (entity extraction → dedup → conflict resolution)
```

Graph memory reduces hallucinations through several mechanisms: the LLM receives verified triples and explicit relationship paths rather than approximate matches; conflict detection flags contradictory information; temporal validity windows prevent presenting outdated facts as current; and every answer can be traced back through specific nodes and edges to source data, enabling auditability critical for regulated industries.

---

## 3. What the research shows: GraphRAG benchmarks

### Microsoft GraphRAG sets the foundation

Microsoft's "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Edge et al., arXiv:2404.16130, 900+ citations) introduced LLM-driven graph indexing with Leiden community detection for hierarchical summarization. It **substantially improves over naïve RAG on comprehensiveness and diversity** for global sensemaking questions, requiring **26–97% fewer tokens** than alternatives. Limitations include high indexing cost and poor incremental update support. **LazyGraphRAG** (2024) and **DRIFT Search** address these as cost-efficient variants.

### HippoRAG demonstrates neuroscience-inspired efficiency

HippoRAG (Gutiérrez et al., NeurIPS 2024) uses knowledge graphs as a hippocampal index with Personalized PageRank for pattern completion. It outperforms SOTA methods by **up to 20% on multi-hop QA** while being **10–30× cheaper and 6–13× faster** than iterative methods like IRCoT. **HippoRAG 2** (Feb 2025) surpasses GraphRAG, RAPTOR, and LightRAG while using significantly fewer offline resources, achieving ~73% recall on MuSiQue and ~95.4% on HotpotQA.

### Agent memory benchmarks from Zep and Mem0

Zep's temporal knowledge graph (Rasmussen et al., arXiv:2501.13956) achieves **94.8% on Deep Memory Retrieval** (vs MemGPT's 93.4%) with **P95 retrieval latency of 300ms** and no LLM calls during retrieval. On LOCOMO, Mem0's graph variant achieves **68.4% accuracy** (26% relative improvement over OpenAI Memory) with **91% lower latency and 90% token cost savings** vs full-context approaches. The graph variant adds ~2% accuracy over base Mem0 but increases median search latency from 0.20s to 0.66s.

### Critical caveat: gains are task-dependent

A key ICLR 2026 finding (GraphRAG-Bench) concludes that **"GraphRAG often fails to outperform vanilla RAG on many NLP tasks."** Benefits concentrate on hierarchical knowledge retrieval and deep contextual reasoning, not simple fact retrieval. An unbiased evaluation framework (arXiv:2506.06331) found GraphRAG's gains are **"much more moderate than reported previously"** when controlling for LLM-as-judge position bias.

---

## 4. Oracle 23ai property graph for agent memory

### SQL/PGQ: standard SQL with graph pattern matching

Oracle 23ai is the **first commercial implementation of SQL:2023 Part 16 (SQL/PGQ)**. Property graphs are metadata-only schema objects that create view-like mappings over existing relational tables — no data materialization. `GRAPH_TABLE` queries are transformed into regular SQL joins under the covers and get full optimizer support.

**Creating the agent memory graph:**

```sql
-- Underlying relational tables
CREATE TABLE agent_entities (
    entity_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR2(500) NOT NULL,
    entity_type VARCHAR2(100),
    summary     VARCHAR2(4000),
    embedding   VECTOR(1536, FLOAT32),
    importance  NUMBER DEFAULT 0.5,
    access_count NUMBER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT SYSTIMESTAMP,
    created_at  TIMESTAMP DEFAULT SYSTIMESTAMP,
    archived    NUMBER(1) DEFAULT 0
);

CREATE TABLE agent_facts (
    fact_id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_entity_id   NUMBER REFERENCES agent_entities(entity_id),
    target_entity_id   NUMBER REFERENCES agent_entities(entity_id),
    predicate          VARCHAR2(200),
    description        VARCHAR2(4000),
    fact_embedding     VECTOR(1536, FLOAT32),
    confidence         NUMBER DEFAULT 0.8,
    t_valid            TIMESTAMP,      -- when the fact became true
    t_invalid          TIMESTAMP,      -- when the fact stopped being true (NULL = still valid)
    t_created          TIMESTAMP DEFAULT SYSTIMESTAMP,
    source_episode_ids VARCHAR2(4000)  -- JSON array of episode IDs
);

-- Property graph definition (metadata-only, no data copied)
CREATE PROPERTY GRAPH agent_memory_graph
  VERTEX TABLES (
    agent_entities KEY (entity_id)
      LABEL entity
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    agent_facts KEY (fact_id)
      SOURCE KEY (source_entity_id) REFERENCES agent_entities (entity_id)
      DESTINATION KEY (target_entity_id) REFERENCES agent_entities (entity_id)
      LABEL fact
      PROPERTIES ALL COLUMNS
  );
```

**Multi-hop graph traversal via SQL/PGQ:**

```sql
-- Find all entities within 1-3 hops of a given entity, filtered by validity
SELECT gt.source_name, gt.predicate, gt.target_name, gt.description
FROM GRAPH_TABLE(agent_memory_graph
    MATCH (e1 IS entity) -[f IS fact]->{1,3} (e2 IS entity)
    WHERE e1.name = :entity_name
      AND f.t_invalid IS NULL
    COLUMNS (e1.name AS source_name, f.predicate, 
             e2.name AS target_name, f.description)
) gt
ORDER BY gt.predicate;
```

**Hybrid graph + vector query (the key Oracle 23ai advantage):**

```sql
-- Graph traversal with vector similarity scoring in one query
SELECT gt.target_name, gt.predicate,
       VECTOR_DISTANCE(e.embedding, :query_vector, COSINE) AS similarity
FROM GRAPH_TABLE(agent_memory_graph
    MATCH (e1 IS entity) -[f IS fact]->{1,3} (e2 IS entity)
    WHERE e1.name = 'Artificial Intelligence'
      AND f.t_invalid IS NULL
    COLUMNS (e2.entity_id AS target_id, e2.name AS target_name,
             f.predicate)
) gt
JOIN agent_entities e ON e.entity_id = gt.target_id
WHERE VECTOR_DISTANCE(e.embedding, :query_vector, COSINE) < 0.4
ORDER BY similarity
FETCH FIRST 20 ROWS ONLY;
```

### PGQL for advanced path queries

Oracle's PGQL (available via Graph Server and Client) supports richer path semantics including shortest path and cheapest path queries:

```sql
-- PGQL: Find shortest path between two entities
SELECT COUNT(e) AS num_hops, ARRAY_AGG(n.name) AS path_nodes
FROM MATCH ANY SHORTEST (p1:entity) (-[e]-(n))* (p2:entity)
    ON agent_memory_graph
WHERE p1.name = 'Alice' AND p2.name = 'ProjectX'
ORDER BY num_hops;

-- PGQL: Variable-length path with named pattern
PATH connected AS () -[e]- ()
SELECT e1.name AS source, e2.name AS target
FROM MATCH (e1) -/:connected*/-> (e2) ON agent_memory_graph
WHERE e1.name = 'Alice';
```

### RDF/SPARQL: when to use it

Use Oracle RDF Graph only if you need OWL inferencing, SPARQL federation with external linked data, or W3C semantic web integration. Oracle's RDF support stores triples in `RDF_LINK$` tables and queries via `SEM_MATCH`:

```sql
SELECT s, p, o FROM TABLE(SEM_MATCH(
  'SELECT ?s ?p ?o WHERE { ?s ?p ?o }',
  SEM_MODELS('agent_rdf_graph'),
  NULL, NULL, NULL, NULL, 'ALLOW_DUP=T', NULL, NULL,
  'AGENT_USER', 'RDF_NETWORK#'
));
```

For agent memory, the property graph model is strongly preferred due to native edge properties, direct SQL integration, and transactional consistency with underlying relational data.

### Oracle Graph Studio and visualization

Graph Studio is a browser-based graph management environment built into **Oracle Autonomous Database only** (not on-premises). It provides interactive notebooks with `%sql`, `%pgql-pgql`, `%sparql-rdf` interpreters, 80+ built-in graph algorithms, and native visualization. For on-premises Oracle 23ai, deploy the Graph Visualization webapp (`graphviz-*.war` on Tomcat) which connects via JDBC and renders graph patterns interactively.

---

## 5. Java/Spring implementation with Oracle Graph

### Spring AI has no built-in graph memory — custom advisors are the path

Spring AI provides `ChatMemory` → `ChatMemoryRepository` for episodic memory and `VectorStoreChatMemoryAdvisor` for semantic memory, but **no graph memory implementation exists**. The extension point is Spring AI's `CallAroundAdvisor` interface, which intercepts prompts to inject graph-derived context and extract entities after generation.

**Complete `GraphMemoryAdvisor` implementation:**

```java
@Component
public class GraphMemoryAdvisor implements CallAroundAdvisor {
    
    private final OracleGraphMemoryStore graphStore;
    private final ChatModel chatModel;
    
    public GraphMemoryAdvisor(OracleGraphMemoryStore graphStore, ChatModel chatModel) {
        this.graphStore = graphStore;
        this.chatModel = chatModel;
    }
    
    @Override
    public AdvisedResponse aroundCall(AdvisedRequest request, CallAroundAdvisorChain chain) {
        String userMessage = request.userText();
        String conversationId = (String) request.adviseContext()
            .get("graph_memory_conversation_id");
        
        // 1. Query graph for relevant context (no LLM calls — fast path)
        String graphContext = graphStore.retrieveRelevantContext(userMessage, conversationId);
        
        // 2. Inject graph context into system prompt
        AdvisedRequest enrichedRequest = AdvisedRequest.from(request)
            .withSystemText(request.systemText() + 
                "\n\nRelevant knowledge from memory:\n" + graphContext)
            .build();
        
        // 3. Execute the LLM call
        AdvisedResponse response = chain.nextAroundCall(enrichedRequest);
        
        // 4. Async: extract entities from conversation turn and store in graph
        String fullTurn = userMessage + "\n" + 
            response.response().getResult().getOutput().getContent();
        graphStore.extractAndStoreAsync(fullTurn, conversationId);
        
        return response;
    }
    
    @Override
    public String getName() { return "GraphMemoryAdvisor"; }
    
    @Override
    public int getOrder() { return 0; } // Run before other advisors
}
```

**Registering the advisor with the ChatClient:**

```java
@Configuration
public class AgentConfig {
    
    @Bean
    public ChatClient chatClient(ChatModel chatModel, ChatMemory chatMemory,
                                  VectorStore vectorStore, GraphMemoryAdvisor graphAdvisor) {
        return ChatClient.builder(chatModel)
            .defaultAdvisors(
                MessageChatMemoryAdvisor.builder(chatMemory).build(),  // Episodic
                QuestionAnswerAdvisor.builder(vectorStore).build(),     // Semantic
                graphAdvisor                                            // Structured
            )
            .build();
    }
}
```

### Entity and relationship extraction via LLM structured output

Spring AI's `BeanOutputConverter` generates JSON Schema from Java records and instructs the LLM to produce structured output:

```java
// Define extraction schema
public record ExtractedEntity(String name, String type, 
                               Map<String, String> properties) {}

public record ExtractedRelationship(String source, String sourceType,
    String relation, String target, String targetType) {}

public record GraphExtractionResult(
    List<ExtractedEntity> entities,
    List<ExtractedRelationship> relationships) {}

@Service
public class EntityExtractionService {
    
    private final ChatClient chatClient;
    
    private static final String EXTRACTION_PROMPT = """
        You are an entity and relationship extractor. Given conversation text,
        extract all entities and relationships as structured data.
        
        Guidelines:
        1. Identify distinct entities (people, organizations, concepts, preferences,
           database objects, technical terms)
        2. Use the most complete, canonical form for entity names
        3. Extract relationships as (source, relation, target) triples
        4. Use general, timeless relationship types: WORKS_AT, KNOWS, PREFERS,
           MANAGES, RELATED_TO, DEPENDS_ON, CAUSED_BY, USES, OWNS
        5. For database/technical entities, use types like Schema, Table, Query,
           Service, Error, Solution
        6. Resolve coreferences: "she" → actual entity name
        """;
    
    public GraphExtractionResult extract(String conversationText) {
        return chatClient.prompt()
            .system(EXTRACTION_PROMPT)
            .user("Extract entities and relationships from:\n" + conversationText)
            .call()
            .entity(GraphExtractionResult.class);
    }
}
```

### Oracle graph access via standard JDBC (SQL/PGQ)

Since SQL/PGQ is standard SQL, it works with Spring's `JdbcTemplate` — no special libraries needed:

```java
@Repository
public class OracleGraphMemoryStore {
    
    private final JdbcTemplate jdbc;
    private final EntityExtractionService extractor;
    private final EmbeddingModel embeddingModel;
    private final AsyncTaskExecutor graphUpdateExecutor;
    
    // Retrieve context: hybrid vector + graph query
    public String retrieveRelevantContext(String query, String conversationId) {
        float[] queryVector = embeddingModel.embed(query);
        
        // Graph traversal + vector similarity in one query
        String sql = """
            SELECT gt.source_name, gt.predicate, gt.target_name, gt.description,
                   VECTOR_DISTANCE(e.embedding, :queryVec, COSINE) AS sim
            FROM GRAPH_TABLE(agent_memory_graph
                MATCH (e1 IS entity) -[f IS fact]-> (e2 IS entity)
                WHERE f.t_invalid IS NULL
                COLUMNS (e1.name AS source_name, f.predicate,
                         e2.name AS target_name, f.description,
                         e2.entity_id AS target_id)
            ) gt
            JOIN agent_entities e ON e.entity_id = gt.target_id
            WHERE VECTOR_DISTANCE(e.embedding, :queryVec, COSINE) < 0.4
            ORDER BY sim FETCH FIRST 20 ROWS ONLY
            """;
        
        List<Map<String, Object>> results = jdbc.queryForList(sql, 
            Map.of("queryVec", queryVector));
        
        StringBuilder context = new StringBuilder();
        for (var row : results) {
            context.append(String.format("%s %s %s: %s\n",
                row.get("source_name"), row.get("predicate"),
                row.get("target_name"), row.get("description")));
        }
        return context.toString();
    }
    
    // Async entity extraction and graph update
    @Async("graphUpdateExecutor")
    @Transactional
    public void extractAndStoreAsync(String text, String conversationId) {
        GraphExtractionResult result = extractor.extract(text);
        
        for (var entity : result.entities()) {
            mergeEntity(entity);
        }
        for (var rel : result.relationships()) {
            mergeFact(rel, conversationId);
        }
    }
    
    private void mergeEntity(ExtractedEntity entity) {
        float[] embedding = embeddingModel.embed(entity.name());
        
        // Check for existing entity via vector similarity (deduplication)
        String findSql = """
            SELECT entity_id, name FROM agent_entities
            WHERE VECTOR_DISTANCE(embedding, :emb, COSINE) < 0.15
            AND archived = 0
            FETCH FIRST 1 ROWS ONLY
            """;
        List<Map<String, Object>> existing = jdbc.queryForList(findSql, 
            Map.of("emb", embedding));
        
        if (existing.isEmpty()) {
            jdbc.update("""
                INSERT INTO agent_entities (name, entity_type, embedding, created_at)
                VALUES (:name, :type, :emb, SYSTIMESTAMP)
                """, Map.of("name", entity.name(), "type", entity.type(), 
                            "emb", embedding));
        } else {
            // Update access count for existing entity
            jdbc.update("UPDATE agent_entities SET access_count = access_count + 1, " +
                "last_accessed = SYSTIMESTAMP WHERE entity_id = :id",
                Map.of("id", existing.get(0).get("entity_id")));
        }
    }
    
    private void mergeFact(ExtractedRelationship rel, String conversationId) {
        // Resolve source and target entity IDs
        Long sourceId = findEntityId(rel.source());
        Long targetId = findEntityId(rel.target());
        if (sourceId == null || targetId == null) return;
        
        String description = rel.source() + " " + rel.relation() + " " + rel.target();
        float[] factEmbedding = embeddingModel.embed(description);
        
        // Check for contradicting facts and invalidate them
        jdbc.update("""
            UPDATE agent_facts SET t_invalid = SYSTIMESTAMP
            WHERE source_entity_id = :srcId AND target_entity_id = :tgtId
              AND predicate = :pred AND t_invalid IS NULL
            """, Map.of("srcId", sourceId, "tgtId", targetId, "pred", rel.relation()));
        
        // Insert new fact
        jdbc.update("""
            INSERT INTO agent_facts 
            (source_entity_id, target_entity_id, predicate, description,
             fact_embedding, t_valid, source_episode_ids)
            VALUES (:srcId, :tgtId, :pred, :desc, :emb, SYSTIMESTAMP, :eps)
            """, Map.of("srcId", sourceId, "tgtId", targetId,
                        "pred", rel.relation(), "desc", description,
                        "emb", factEmbedding, "eps", "[\"" + conversationId + "\"]"));
    }
}
```

### PGQL alternative via Oracle Graph Client

For richer path queries (shortest path, cheapest path), use the PGQL JDBC driver:

```java
// Maven: com.oracle.database.graph:opg-client:25.3.0
import oracle.pg.rdbms.pgql.PgqlConnection;
import oracle.pg.rdbms.pgql.PgqlStatement;
import oracle.pg.rdbms.pgql.PgqlResultSet;

Connection conn = dataSource.getConnection();
PgqlConnection pgqlConn = PgqlConnection.getConnection(conn);
pgqlConn.setGraph("AGENT_MEMORY_GRAPH");

String pgql = """
    SELECT e1.name AS source, label(r) AS predicate, e2.name AS target
    FROM MATCH (e1) -[r]-> (e2) ON agent_memory_graph
    WHERE e1.name = 'Alice'
    """;
PgqlResultSet rs = pgqlConn.createStatement().executeQuery(pgql);
while (rs.next()) {
    System.out.println(rs.getString("source") + " -> " + rs.getString("target"));
}
```

### Python reference: LangChain and Mem0 patterns

For comparison, here's how LangChain and Mem0 implement graph memory extraction:

```python
# LangChain: LLMGraphTransformer + Neo4j
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document

transformer = LLMGraphTransformer(
    llm=ChatOpenAI(temperature=0, model="gpt-4o"),
    allowed_nodes=["Person", "Organization", "Concept", "Preference"],
    allowed_relationships=["WORKS_AT", "KNOWS", "PREFERS", "MANAGES"],
    node_properties=True, relationship_properties=True
)
docs = transformer.convert_to_graph_documents(
    [Document(page_content="Alice works at Google. She manages the ML team with Bob.")]
)
# Result: (Alice)-[WORKS_AT]->(Google), (Alice)-[MANAGES]->(ML team)

# Mem0: Graph memory with automatic extraction
from mem0 import Memory
config = {"graph_store": {"provider": "neo4j", "config": {
    "url": NEO4J_URL, "username": "neo4j", "password": PASSWORD}}}
memory = Memory.from_config(config)
memory.add([
    {"role": "user", "content": "I work at Google on the ML team with Bob."},
    {"role": "assistant", "content": "Great! What's your focus?"},
], user_id="alice")
results = memory.search("Who works with Alice?", user_id="alice")
# Returns both vector results AND graph relations
```

### SPARQL from Java (Apache Jena)

If RDF is needed for ontology reasoning:

```java
import org.apache.jena.query.*;

String sparql = """
    PREFIX kg: <http://example.org/kg/>
    SELECT ?entity ?prop ?value
    WHERE {
        ?source kg:name "Alice" .
        ?source ?rel ?entity .
        ?entity ?prop ?value .
    } LIMIT 50
    """;
try (QueryExecution qexec = QueryExecutionFactory.create(sparql, model)) {
    ResultSet results = qexec.execSelect();
    while (results.hasNext()) {
        QuerySolution soln = results.nextSolution();
        // Process results...
    }
}
```

---

## 6. Practical patterns for combining all three memory types

### The unified retrieval pipeline

The recommended architecture for your Oracle Database agent combines all three existing memory types with the new graph layer in a single-database design:

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT CONTROLLER                      │
│  Spring AI ChatClient + Advisors                         │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Chat     │  │  Vector      │  │  Knowledge       │  │
│  │  History  │  │  Store       │  │  Graph           │  │
│  │  (FIFO)   │  │  (Semantic)  │  │  (Structured)    │  │
│  │  Last N   │  │  Oracle AI   │  │  Oracle SQL/PGQ  │  │
│  │  messages │  │  Vector      │  │  Property Graph   │  │
│  │  table    │  │  Search      │  │  on entity/fact   │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       └───────────────┼────────────────────┘             │
│               ┌───────▼────────┐                         │
│               │  CONTEXT       │  RRF Merge + Rerank     │
│               │  ASSEMBLER     │  Token budgeting         │
│               └───────┬────────┘                         │
│               ┌───────▼────────┐                         │
│               │  LLM + @Tool   │                         │
│               └───────┬────────┘                         │
│               ┌───────▼────────┐                         │
│               │  ASYNC GRAPH   │  @Async extraction      │
│               │  UPDATER       │  Fact resolution         │
│               └────────────────┘                         │
└──────────────────────────────────────────────────────────┘
           ALL IN ONE ORACLE DATABASE
```

The retrieval sequence per conversation turn follows Zep/Mem0/MAGMA patterns: query analysis (intent classification + NER + embedding generation) → parallel fan-out to all three memory stores → Reciprocal Rank Fusion merge with cross-encoder reranking → context assembly with token budgeting → LLM generation → async graph update on a separate thread.

### Entity and relationship types for a database agent

For an Oracle Database agent specifically, the most useful entity types extend beyond generic categories:

| Node Type | Description | Examples |
|---|---|---|
| `Person` | Users, contacts | "Alice", "Bob the DBA" |
| `Organization` | Companies, teams | "Acme Corp", "Engineering Team" |
| `Concept` | Abstract ideas, preferences | "Agile", "Machine Learning" |
| `Schema` | Database schema elements | "HR.EMPLOYEES", "IDX_SALARY" |
| `Query` | SQL query patterns | "Monthly revenue report" |
| `Error` | Error patterns | "ORA-01555", "Deadlock on ORDERS" |
| `Solution` | Resolved approaches | "Partition pruning fix" |

**Essential edge properties** (following Zep's bi-temporal model): `t_valid` (when the fact became true), `t_invalid` (NULL = still valid), `t_created` (when the system learned this), confidence score, source episode IDs, and access count. **Never physically delete facts** — always soft-delete with temporal markers to preserve full history for temporal reasoning.

### Graph memory updates and deduplication

Process every conversation turn, but use significance filtering. The fast path (always synchronous) updates chat history and vector store. The graph path (asynchronous) extracts entities and facts via LLM, resolves entities through vector similarity search against existing nodes (threshold ~0.15 cosine distance), and resolves conflicts through temporal edge invalidation — when new information contradicts an existing edge, set `t_invalid` on the old edge and create a new one.

### Forgetting and memory decay

Implement Ebbinghaus-inspired decay with nightly maintenance:

```java
@Scheduled(cron = "0 0 2 * * *") // Nightly
public void performMemoryMaintenance() {
    // Score all entities
    String scoreSql = """
        UPDATE agent_entities SET importance = 
            0.3 * POWER(0.995, (SYSTIMESTAMP - last_accessed) * 24) +
            0.2 * LN(1 + access_count) / 10 +
            0.3 * importance +
            0.2 * (SELECT COUNT(*) FROM agent_facts 
                    WHERE source_entity_id = entity_id OR target_entity_id = entity_id) / 100
        WHERE archived = 0
        """;
    jdbc.update(scoreSql);
    
    // Archive cold entities (importance < 0.1, not accessed in 30+ days)
    jdbc.update("""
        UPDATE agent_entities SET archived = 1
        WHERE importance < 0.1 
          AND last_accessed < SYSTIMESTAMP - INTERVAL '30' DAY
          AND archived = 0
        """);
}
```

Tier the graph into hot (score > 0.7, always retrieved), warm (0.3–0.7, retrieved when relevant), and cold (< 0.3, archived but queryable on demand).

## Conclusion

Knowledge graph memory fills a precise gap in the existing Oracle Database agent architecture: **structured, multi-hop reasoning that vector search cannot provide**. The research is clear that neither graph nor vector alone is optimal — **hybrid architectures consistently deliver the strongest results**, with graph providing 10–40+ percentage point improvements specifically on multi-hop and entity-centric queries.

Oracle 23ai's SQL/PGQ standard offers a uniquely elegant implementation path. Because property graphs are metadata-only views over relational tables, you can store entities and facts in regular tables (with `VECTOR` columns for embeddings), define a `CREATE PROPERTY GRAPH` mapping, and query with `GRAPH_TABLE` in standard SQL — all through your existing JDBC connection pool and Spring `@Transactional` infrastructure. No separate graph database deployment, no new connection management, and full ACID guarantees across chat history, vectors, and graph in one database.

The implementation follows three key principles drawn from production systems like Zep and Mem0. First, **no LLM calls during retrieval** — use vector indexes, BM25, and graph traversal only at query time, reserving LLM calls for the slower ingestion path. Second, **bi-temporal fact management** — every edge tracks when the fact was true in the world and when the system learned it, enabling temporal reasoning without data loss. Third, **async graph updates** — keep the response-path latency low by decoupling entity extraction and conflict resolution onto background threads via Spring's `@Async`. The target is P95 retrieval under 300ms, achievable with Oracle's optimizer handling the `GRAPH_TABLE` → SQL translation efficiently.