package dev.victormartin.agentmemory.chatserver.retriever;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.document.Document;
import org.springframework.ai.rag.Query;
import org.springframework.ai.rag.retrieval.search.DocumentRetriever;
import org.springframework.jdbc.core.JdbcTemplate;

public class OracleHybridDocumentRetriever implements DocumentRetriever {

    private static final Logger log = LoggerFactory.getLogger(OracleHybridDocumentRetriever.class);

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    private final int topK;
    private final String indexName;
    private final String scorer;

    public OracleHybridDocumentRetriever(JdbcTemplate jdbcTemplate,
                                          int topK,
                                          String indexName,
                                          String scorer) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = new ObjectMapper();
        this.topK = topK;
        this.indexName = indexName;
        this.scorer = scorer;
    }

    @Override
    public List<Document> retrieve(Query query) {
        log.info("[SEMANTIC] Hybrid search for: \"{}\"", query.text());
        String searchJson = buildSearchJson(query.text());
        log.debug("[SEMANTIC] Hybrid search JSON: {}", searchJson);

        String resultJson = jdbcTemplate.queryForObject(
                "SELECT DBMS_HYBRID_VECTOR.SEARCH(JSON(?)) FROM DUAL",
                String.class,
                searchJson);

        if (resultJson == null || resultJson.isBlank()) {
            log.info("[SEMANTIC] Hybrid search returned 0 documents");
            return List.of();
        }

        return parseResults(resultJson);
    }

    private List<Document> parseResults(String resultJson) {
        try {
            List<Map<String, Object>> results = objectMapper.readValue(
                    resultJson, new TypeReference<>() {});
            List<Document> documents = new ArrayList<>();
            for (Map<String, Object> result : results) {
                String chunkText = (String) result.get("chunk_text");
                if (chunkText == null || chunkText.isBlank()) {
                    continue;
                }
                Map<String, Object> metadata = new HashMap<>();
                metadata.put("score", result.get("score"));
                metadata.put("vector_score", result.get("vector_score"));
                metadata.put("text_score", result.get("text_score"));
                documents.add(new Document(chunkText, metadata));
            }
            log.info("[SEMANTIC] Hybrid search returned {} documents (best score: {})",
                    documents.size(),
                    documents.isEmpty() ? "N/A" : documents.get(0).getMetadata().get("score"));
            return documents;
        } catch (Exception e) {
            log.error("Failed to parse hybrid search results", e);
            return List.of();
        }
    }

    private String buildSearchJson(String queryText) {
        String escaped = escapeJson(queryText);
        String containsClause = buildContainsClause(queryText);
        return """
            {
              "hybrid_index_name": "%s",
              "search_scorer": "%s",
              "search_fusion": "UNION",
              "vector": {
                "search_text": "%s"
              },
              "text": {
                "contains": "%s"
              },
              "return": {
                "values": ["chunk_text", "score", "vector_score", "text_score"],
                "topN": %d
              }
            }
            """.formatted(indexName, scorer, escaped, containsClause, topK);
    }

    // Oracle Text operators that must not appear as search terms
    private static final java.util.Set<String> ORACLE_TEXT_RESERVED = java.util.Set.of(
            "and", "or", "not", "near", "within", "about", "accum", "minus", "equiv");

    private String buildContainsClause(String queryText) {
        String cleaned = escapeOracleText(queryText);
        String[] words = cleaned.split("\\s+");
        var terms = java.util.Arrays.stream(words)
                .filter(w -> !w.isBlank() && w.length() > 2)
                .filter(w -> !ORACLE_TEXT_RESERVED.contains(w.toLowerCase()))
                .toList();
        if (terms.isEmpty()) {
            return cleaned.isBlank() ? "dummy" : cleaned;
        }
        return String.join(" OR ", terms);
    }

    private String escapeJson(String text) {
        return text.replace("\\", "\\\\")
                   .replace("\"", "\\\"")
                   .replace("\n", "\\n");
    }

    private String escapeOracleText(String text) {
        // Keep only alphanumeric characters and spaces — safer than blacklisting
        // Oracle Text special chars individually
        return text.replaceAll("[^a-zA-Z0-9\\s]", " ")
                   .replaceAll("\\s+", " ")
                   .trim();
    }
}
