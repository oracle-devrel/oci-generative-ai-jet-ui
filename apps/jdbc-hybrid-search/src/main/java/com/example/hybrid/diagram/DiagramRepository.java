package com.example.hybrid.diagram;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public final class DiagramRepository {
    private static final String COSINE_DISTANCE_SQL = """
            select vector_distance(a.embedding, b.embedding, COSINE) as cosine_distance
            from hybrid_documents a, hybrid_documents b
            where a.title = ?
              and b.title = ?
            """;

    private static final String DIAGRAM_DOCUMENTS_SQL = """
            select title,
                   category,
                   json_value(metadata, '$.audience') as audience
            from hybrid_documents
            order by title
            """;

    private final DataSource dataSource;

    public DiagramRepository(DataSource dataSource) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
    }

    public List<DiagramDocument> listDiagramDocuments() {
        List<DiagramDocument> documents = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(DIAGRAM_DOCUMENTS_SQL);
             ResultSet resultSet = statement.executeQuery()) {
            while (resultSet.next()) {
                documents.add(new DiagramDocument(
                        resultSet.getString("title"),
                        resultSet.getString("category"),
                        resultSet.getString("audience")
                ));
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Unable to load diagram documents", exception);
        }
        return documents;
    }

    public double cosineDistanceBetween(String firstTitle, String secondTitle) {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(COSINE_DISTANCE_SQL)) {
            statement.setString(1, firstTitle);
            statement.setString(2, secondTitle);
            try (ResultSet resultSet = statement.executeQuery()) {
                if (!resultSet.next()) {
                    throw new IllegalArgumentException("Unable to compute cosine distance between requested documents");
                }
                return resultSet.getDouble("cosine_distance");
            }
        } catch (SQLException exception) {
            throw new IllegalStateException("Unable to compute cosine distance", exception);
        }
    }
}
