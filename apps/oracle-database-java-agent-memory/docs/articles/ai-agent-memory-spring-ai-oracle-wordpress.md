---
title: "Build AI Agent Memory with Spring AI and Oracle Database 26ai"
description: "Learn how to give an AI agent persistent episodic, semantic, and procedural memory using Spring AI, Oracle Database 26ai Hybrid Vector Indexes, and in-database ONNX embeddings."
primary_keyword: "AI agent memory"
products: ["Oracle AI Database 26ai", "Oracle Hybrid Vector Indexes"]
audience: ["Developers", "AI engineers"]
---

# How I Gave Memory to an AI Agent Using Spring AI and Oracle Database

<!-- wp:paragraph -->
<p><strong>TL;DR:</strong> LLMs forget everything between sessions. This post shows how to build three types of persistent memory — episodic (chat history), semantic (domain knowledge via hybrid search), and procedural (tool calls) — using Spring AI and a single Oracle Database 26ai instance.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Why This Matters</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Every LLM has the same problem: it forgets everything the moment the conversation ends, sometimes even during long conversations. Spend twenty minutes explaining your project setup, your constraints, your preferences — and it nails the answer. Close the tab, open a new session, and it greets you like a stranger. All that context, gone.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>If you want to build an AI <em>agent</em> — something that actually remembers context, knows things about your domain, and can take action — you need to give it memory. The practical kind, where it remembers what you said, retrieves facts you taught it, and executes real workflows backed by database queries.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>This post walks through a proof of concept that does exactly that. Three types of memory, one database, not much code.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">What You'll Learn</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li>How to implement episodic, semantic, and procedural memory for an AI agent using Spring AI advisors and <code>@Tool</code> methods</li>
<li>How to use Oracle Database 26ai Hybrid Vector Indexes (vector + keyword search fused with Reciprocal Rank Fusion) for semantic retrieval</li>
<li>How to compute embeddings in-database with a loaded ONNX model — no external embedding API calls</li>
<li>How to wire it all together with one database, one connection pool, and minimal configuration</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Architecture Overview</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The agent runs on Spring Boot with Spring AI. Ollama handles chat inference (qwen2.5) locally. Oracle AI Database 26ai stores all three memory types: a relational table for chat history (episodic), a hybrid vector index for domain knowledge retrieval (semantic), and application tables queried by <code>@Tool</code> methods (procedural). Embeddings are computed in-database by a loaded ONNX model (all-MiniLM-L12-v2), so there are no external embedding API calls. A Streamlit frontend provides a simple web UI.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Both advisors and all six tools run on every request. The agent simultaneously remembers what you said, looks up relevant knowledge, and knows how to perform tasks — all from a single Oracle Database instance. No Pinecone. No Redis. No second database. One connection pool, one set of credentials, one thing to monitor.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Prerequisites</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li>Java 21</li>
<li>Gradle 8.14</li>
<li>Oracle AI Database 26ai (container or instance)</li>
<li>Ollama with the <code>qwen2.5</code> model pulled</li>
<li>Python 3.x with Streamlit (optional, for the web UI)</li>
<li>The ONNX model file (<code>all_MiniLM_L12_v2.onnx</code>) for in-database embeddings</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Step-by-Step Guide</h2>
<!-- /wp:heading -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Step 1: Set Up the Oracle Database and Hybrid Vector Index</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Start an Oracle AI Database 26ai instance and run the one-time setup script to load the ONNX embedding model and create the hybrid vector index. This enables in-database embeddings and combined vector + keyword search.</p>
<!-- /wp:paragraph -->

<!-- wp:code -->
<pre class="wp-block-code"><code>-- Load the ONNX model for in-database embeddings
BEGIN
  DBMS_VECTOR.LOAD_ONNX_MODEL(
    directory  => 'DM_DUMP',
    file_name  => 'all_MiniLM_L12_v2.onnx',
    model_name => 'ALL_MINILM_L12_V2'
  );
END;
/

-- Create a hybrid index: vector similarity + Oracle Text keyword search
CREATE HYBRID VECTOR INDEX POLICY_HYBRID_IDX
ON POLICY_DOCS(content)
PARAMETERS('MODEL ALL_MINILM_L12_V2 VECTOR_IDXTYPE HNSW');
</code></pre>
<!-- /wp:code -->

<!-- wp:paragraph -->
<p>Once the index exists, embeddings are computed automatically when rows are inserted — no external embedding API calls needed.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Step 2: Define Procedural Memory with @Tool Methods</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Procedural memory is implemented as <code>@Tool</code>-annotated methods in a Spring component. These are real database queries via JPA that the LLM can call when it decides a task requires action, not just an answer. The <code>@Tool</code> description tells the LLM <em>when</em> to use each method, and <code>@ToolParam</code> describes the arguments.</p>
<!-- /wp:paragraph -->

<!-- wp:code -->
<pre class="wp-block-code"><code>@Tool(description = "Look up the status of a customer order by its order ID. " +
        "Returns the current status including shipping information.")
public String lookupOrderStatus(
        @ToolParam(description = "The order ID to look up, e.g. ORD-1001") String orderId) {
    // Fetches order from DB via JPA, returns formatted status string
}

@Tool(description = "Initiate a product return for a given order. " +
        "Validates the order exists, checks that it is in DELIVERED status, " +
        "and verifies the return is within the 30-day return window.")
public String initiateReturn(
        @ToolParam(description = "The order ID to return") String orderId,
        @ToolParam(description = "The reason for the return") String reason) {
    // Validates order exists, checks DELIVERED status and 30-day window, updates status via JPA
}
</code></pre>
<!-- /wp:code -->

<!-- wp:paragraph -->
<p>The full class has six tools: <code>getCurrentDateTime</code>, <code>listOrders</code>, <code>lookupOrderStatus</code>, <code>initiateReturn</code>, <code>escalateToSupport</code>, and <code>listSupportTickets</code>. The LLM decides <em>when</em> to act; the Java methods define <em>how</em>.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Step 3: Wire the Controller with Advisors and Tools</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The controller builds a single <code>ChatClient</code> with two advisors and six tools. <code>MessageChatMemoryAdvisor</code> handles episodic memory — it loads the last 100 messages for the current conversation from a relational table and saves each new exchange. <code>RetrievalAugmentationAdvisor</code> with a custom <code>OracleHybridDocumentRetriever</code> handles semantic memory — it calls <code>DBMS_HYBRID_VECTOR.SEARCH</code> to run vector + keyword search in parallel, fused with Reciprocal Rank Fusion (RRF). The tools are registered via <code>.defaultTools(agentTools)</code>.</p>
<!-- /wp:paragraph -->

<!-- wp:code -->
<pre class="wp-block-code"><code>@RestController
@RequestMapping("/api/v1/agent")
public class AgentController {

    public AgentController(ChatClient.Builder builder,
                           JdbcChatMemoryRepository chatMemoryRepository,
                           JdbcTemplate jdbcTemplate,
                           AgentTools agentTools) {
        // Builds a ChatClient with:
        //   - MessageChatMemoryAdvisor (episodic: last 100 messages per conversation)
        //   - RetrievalAugmentationAdvisor + OracleHybridDocumentRetriever (semantic: hybrid search)
        //   - AgentTools via .defaultTools() (procedural: 6 @Tool methods)
        //   - System prompt defining the agent persona and tool usage rules
    }

    @PostMapping("/chat")
    public ResponseEntity&lt;String&gt; chat(
            @RequestBody String message,
            @RequestHeader("X-Conversation-Id") String conversationId) {
        // Sends message to ChatClient with conversation ID, returns LLM response
    }

    @PostMapping("/knowledge")
    public ResponseEntity&lt;String&gt; addKnowledge(@RequestBody String content) {
        // Inserts text into POLICY_DOCS table via JDBC (hybrid index handles embedding)
    }
}
</code></pre>
<!-- /wp:code -->

<!-- wp:paragraph -->
<p>All three memory types run on every request. The agent simultaneously remembers what you said, looks up relevant knowledge, and knows how to perform tasks.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Step 4: Implement the Hybrid Document Retriever</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The custom <code>OracleHybridDocumentRetriever</code> implements Spring AI's <code>DocumentRetriever</code> interface and calls <code>DBMS_HYBRID_VECTOR.SEARCH</code> via JDBC. It passes a JSON parameter specifying the hybrid index, the RRF scorer, and a keyword match clause. This bypasses <code>OracleVectorStore</code> entirely for retrieval.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Why hybrid instead of pure vector search? Dense embeddings capture meaning — a query about "return policy" will match documents about refunds and exchanges. But they're weak on exact terms: a query for "ORD-1001" degrades because the embedding model encodes semantics, not keywords. Hybrid search covers both: the vector side handles meaning, the keyword side handles exact matches, and RRF merges the two result lists by rank position.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Step 5: Run the Application</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Start the Oracle DB container, install Ollama, pull the chat model, run the Spring Boot backend with the <code>local</code> profile, and optionally start the Streamlit UI.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Quick test with curl:</strong></p>
<!-- /wp:paragraph -->

<!-- wp:code -->
<pre class="wp-block-code"><code>curl -X POST http://localhost:8080/api/v1/agent/chat \
  -H "Content-Type: text/plain" \
  -H "X-Conversation-Id: test-1" \
  -d "What orders do I have?"
</code></pre>
<!-- /wp:code -->

<!-- wp:paragraph -->
<p>The agent will use procedural memory (the <code>listOrders</code> tool) to query the database and return the demo orders. Try following up with "What is your return policy?" to see semantic memory (hybrid search over policy documents) in action, then "My name is Victor" followed later by "What's my name?" to test episodic memory.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Validation &amp; Troubleshooting</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li><strong>Hybrid index not returning results:</strong> Verify the ONNX model was loaded successfully with <code>SELECT MODEL_NAME FROM USER_MINING_MODELS</code>. Confirm the hybrid index was created with <code>SELECT INDEX_NAME FROM USER_INDEXES WHERE INDEX_NAME = 'POLICY_HYBRID_IDX'</code>.</li>
<li><strong>Chat memory not persisting:</strong> Check that the <code>SPRING_AI_CHAT_MEMORY</code> table was auto-created (<code>initialize-schema: always</code> in <code>application.yaml</code>). Verify you are sending the same <code>X-Conversation-Id</code> header across requests.</li>
<li><strong>Tools not being called:</strong> Ensure the <code>@Tool</code> descriptions are clear enough for the LLM to match. Check Ollama logs for tool-calling output. The <code>qwen2.5</code> model supports tool calling natively.</li>
<li><strong>Slow first query:</strong> The first request loads chat history and warms up the hybrid index. Subsequent requests in the same conversation should be faster.</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Key Takeaways</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li><strong>LLMs forget everything between sessions.</strong> Episodic, semantic, and procedural memory fix that — chat history, domain knowledge retrieval, and actionable tool calls, all persisted in the database.</li>
<li><strong>One database handles it all.</strong> Oracle AI Database 26ai stores chat history, runs hybrid vector search, and hosts the application tables — no need to bolt on a separate vector database or search engine.</li>
<li><strong>Hybrid search beats pure vector search.</strong> Combining dense embeddings with keyword matching (fused via Reciprocal Rank Fusion) means the agent finds documents by meaning <em>and</em> by exact terms like order IDs.</li>
<li><strong>Embeddings stay in the database.</strong> A loaded ONNX model computes embeddings on insert — no external embedding API calls, no extra infrastructure.</li>
<li><strong>Agent memory doesn't have to be complicated.</strong> Two advisors, six tools backed by real database tables, one database, and the LLM stops forgetting.</li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Frequently Asked Questions</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>Why does the agent need three types of memory instead of just chat history?</strong><br>Chat history (episodic memory) only covers what was said in the conversation. Semantic memory lets the agent retrieve domain knowledge — like return policies or shipping rules — that was never mentioned in chat. Procedural memory lets it take actions, such as looking up an order or initiating a return, by calling tool methods backed by real database queries.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Why use hybrid search instead of plain vector similarity?</strong><br>Pure vector search matches by meaning, which works well for natural-language questions but struggles with exact terms like product codes or order IDs. Hybrid search runs vector and keyword search in parallel and merges the results by rank position (Reciprocal Rank Fusion), so the agent finds relevant documents whether the match is semantic, lexical, or both.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Do I need a separate vector database to build this?</strong><br>No. Oracle AI Database 26ai supports relational tables, hybrid vector indexes, and full-text search in a single instance. The POC uses one connection pool and one set of credentials for chat history, vector retrieval, and all application data.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>How are the embeddings generated?</strong><br>An ONNX model (all-MiniLM-L12-v2) is loaded directly into Oracle Database. Embeddings are computed automatically whenever a row is inserted into the indexed table — no external API calls and no separate embedding service required.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>What are the limitations?</strong><br>This is a proof of concept. There's no authentication, no rate limiting, and no streaming responses. It demonstrates the architecture and approach — production use would require hardening those areas.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Next Steps</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li><a href="https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/oracle-database-java-agent-memory">GitHub repo</a></li>
<li><a href="https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/">Oracle AI Vector Search documentation</a></li>
<li><a href="https://docs.spring.io/spring-ai/reference/">Spring AI documentation</a></li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Authors</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li><strong>Victor Martin</strong> – Senior Principal Product Manager, Oracle<br>
Building AI-powered applications with Oracle Database and Spring AI.<br>
<a href="https://www.linkedin.com/in/victormartindeveloper/">LinkedIn</a></li>
</ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Contributors</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li><strong>Victor Martin</strong> – Senior Principal Product Manager at Oracle Database</li>
</ul>
<!-- /wp:list -->
