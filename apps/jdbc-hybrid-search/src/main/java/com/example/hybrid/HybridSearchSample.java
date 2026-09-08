package com.example.hybrid;

import com.example.hybrid.diagram.DiagramGenerator;
import oracle.jdbc.datasource.impl.OracleDataSource;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class HybridSearchSample {
    static final String INSERT_SQL = """
            insert into hybrid_documents (title, content, category, price, metadata, embedding)
            values (?, ?, ?, ?, ?, ?)
            """;

    // Blend vector ranking with relational and JSON filters in one JDBC query.
    private static final String HYBRID_SEARCH_SQL = """
            select id, title, category, price, audience, score
            from (
                select id,
                       title,
                       category,
                       price,
                       json_value(metadata, '$.audience') as audience,
                       (1 - vector_distance(embedding, ?, COSINE)) as score
                from hybrid_documents
                where category = ?
                  and price <= ?
                  and json_value(metadata, '$.audience') = ?
                  and json_exists(metadata, '$.topics[*]?(@ == $topic)' passing ? as "topic")
            )
            where score >= ?
            order by score desc, price, title
            fetch first ? rows only
            """;

    // Minimum similarity score used for vector ranking
    private static final double MIN_SCORE = 0.70d;

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            System.err.println("Usage: <jdbcUrl> <username> <password>");
            System.exit(1);
        }

        OracleDataSource dataSource = createDataSource(args[0], args[1], args[2]);

        try (Connection connection = dataSource.getConnection()) {
            List<Document> documents = SampleDataLoader.loadSampleData(connection);

            SearchRequest request = new SearchRequest(
                    "oracle jdbc vector search for beginners",
                    "tutorial",
                    50.0,
                    "beginner",
                    "vector",
                    3,
                    MIN_SCORE
            );
            List<SearchResult> results = search(connection, request);
            validateExpectedResults(results);

            System.out.println("Loaded documents: " + documents.size());
            System.out.println("Hybrid search for: " + request.text());
            results.forEach(result -> System.out.printf(
                    Locale.US,
                    "%s | category=%s | price=%.2f | audience=%s | score=%.4f%n",
                    result.title(),
                    result.category(),
                    result.price(),
                    result.audience(),
                    result.score()
            ));

            new DiagramGenerator(dataSource).writeSvg();
        }
    }

    static List<SearchResult> search(Connection connection, SearchRequest request) throws SQLException {
        List<SearchResult> results = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(HYBRID_SEARCH_SQL)) {
            statement.setObject(1, VectorUtil.embedToFloat32VECTOR(request.text()));
            statement.setString(2, request.category());
            statement.setDouble(3, request.maxPrice());
            statement.setString(4, request.audience());
            statement.setString(5, request.topic());
            statement.setDouble(6, request.minScore());
            statement.setInt(7, request.maxResults());
            try (ResultSet resultSet = statement.executeQuery()) {
                while (resultSet.next()) {
                    results.add(new SearchResult(
                            resultSet.getLong("id"),
                            resultSet.getString("title"),
                            resultSet.getString("category"),
                            resultSet.getDouble("price"),
                            resultSet.getString("audience"),
                            resultSet.getDouble("score")
                    ));
                }
            }
        }
        return results;
    }

    static void validateExpectedResults(List<SearchResult> results) {
        if (results.size() != 2) {
            throw new IllegalStateException("Expected 2 hybrid-search results but found " + results.size());
        }
        if (!"Oracle Vector Search for Beginners".equals(results.get(0).title())) {
            throw new IllegalStateException("Expected first result to be Oracle Vector Search for Beginners but was " + results.get(0).title());
        }
        if (!"Budget-Friendly Hybrid Search Recipes".equals(results.get(1).title())) {
            throw new IllegalStateException("Expected second result to be Budget-Friendly Hybrid Search Recipes but was " + results.get(1).title());
        }
    }

    static OracleDataSource createDataSource(String url, String username, String password) throws SQLException {
        OracleDataSource ds = new OracleDataSource();
        ds.setURL(url);
        ds.setUser(username);
        ds.setPassword(password);
        return ds;
    }
}
