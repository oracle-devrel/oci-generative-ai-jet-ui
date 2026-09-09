package com.example.news.genai.vectorstore;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import com.example.news.model.News;
import com.example.news.model.NewsDTO;
import com.example.news.model.SearchRequest;
import com.oracle.spring.json.jsonb.JSONB;
import oracle.jdbc.OracleType;
import oracle.jdbc.OracleTypes;
import oracle.sql.VECTOR;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.springframework.stereotype.Component;

/**
 * This sample class provides a vector abstraction for Oracle AI Database 26ai.
 * The sample class includes capabilities to create a table for embeddings, add embeddings, and execute similarity searches
 * against embeddings stored in the database.
 *
 * @author  Anders Swanson
 */
@Component
public class NewsStore {
    /**
     * A batch size of 50 to 100 records is recommending for bulk inserts.
     */
    private static final int BATCH_SIZE = 50;

    private final VectorDataAdapter dataAdapter;
    private final JSONB jsonb;

    public NewsStore(VectorDataAdapter dataAdapter, JSONB jsonb) {
        this.dataAdapter = dataAdapter;
        this.jsonb = jsonb;
    }

    /**
     * Adds a list of Embeddings to the vector store, in batches.
     * @param newsList To add.
     * @param connection Database connection used for upsert.
     */
    public void addAll(ConsumerRecords<String, News> newsList, Connection connection) {
        final String sql = """
                insert into news_dv (data) values(?)
                """;
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            int i = 0;
            for (ConsumerRecord<String, News> record : newsList) {
                News news = record.value();
                byte[] oson = jsonb.toOSON(news);

                news.setNews_vector(new ArrayList<>());
                stmt.setObject(1, oson, OracleTypes.JSON);
                stmt.addBatch();

                // If BATCH_SIZE records have been added to the statement, execute the batch.
                if (i % BATCH_SIZE == BATCH_SIZE - 1) {
                    stmt.executeBatch();
                }
                i++;
            }
            // If there are any remaining batches, execute them.
            if (newsList.count() % BATCH_SIZE != 0) {
                stmt.executeBatch();
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

public List<NewsDTO> search(SearchRequest searchRequest, VECTOR vector, Connection connection) {
        // This query is designed to:
        // 1. Calculate a similarity score for each row based on the cosine distance between the embedding column
        // and a given vector using the "vector_distance" function.
        // 2. Order the rows by this similarity score in descending order.
        // 3. Filter out rows with a similarity score below a specified threshold.
        // 4. Return only the top rows that meet the criteria.
        // 5. Group by article ID, so multiple chunks from the same article do not duplicate results.
        final String searchQuery = """
            select n.news_id, n.article, nv.score
            from news n
            join (
                select news_id, max(score) as score
                from (
                    select news_id, (1 - vector_distance(embedding, ?, cosine)) as score
                    from news_vector
                    order by score desc
                )
                where score >= ?
                group by news_id
                order by score desc
                fetch first 5 rows only
            ) nv on n.news_id = nv.news_id
            order by nv.score desc""";

        List<NewsDTO> matches = new ArrayList<>();
        try (PreparedStatement stmt = connection.prepareStatement(searchQuery)) {
            // When using the VECTOR data type with prepared statements, always use setObject with the OracleType.VECTOR targetSqlType.
            stmt.setObject(1, vector, OracleType.VECTOR.getVendorTypeNumber());
            stmt.setObject(2, searchRequest.getMinScore(), OracleType.NUMBER.getVendorTypeNumber());
            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    matches.add(fromResultSet(rs));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
        return matches;
    }

    public Optional<NewsDTO> findByID(String id, Connection conn) throws SQLException {
        final String sql = "select * from news where news_id = ?";
        try (PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setString(1, id);
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(fromResultSet(rs));
                }
            }
        }
        return Optional.empty();
    }

    public void cleanup(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement()) {
            stmt.executeQuery("truncate table news_vector");
            stmt.executeQuery("truncate table news");
        }
    }

    private NewsDTO fromResultSet(ResultSet rs) throws SQLException {
        return new NewsDTO(
                rs.getString("news_id"),
                rs.getString("article")
        );
    }
}
