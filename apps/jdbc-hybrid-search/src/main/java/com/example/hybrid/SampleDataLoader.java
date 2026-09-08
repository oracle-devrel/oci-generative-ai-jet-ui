package com.example.hybrid;

import jakarta.json.Json;
import jakarta.json.JsonArray;
import jakarta.json.JsonObject;
import jakarta.json.JsonReader;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

import static com.example.hybrid.HybridSearchSample.INSERT_SQL;

public final class SampleDataLoader {
    private static final String DOCUMENTS_RESOURCE = "/documents.json";
    private static final String SCHEMA_RESOURCE = "/schema.sql";

    private SampleDataLoader() {
    }

    public static List<Document> loadSampleData(Connection connection) throws SQLException, IOException {
        applySchema(connection, SCHEMA_RESOURCE);
        List<Document> documents = loadDocuments(DOCUMENTS_RESOURCE);
        seedSampleData(connection, documents);
        return documents;
    }

    static void applySchema(Connection connection, String resourcePath) throws IOException, SQLException {
        String script = readResource(resourcePath);
        for (String rawStatement : script.split("(?m)^/\\s*$")) {
            String ddl = rawStatement.trim();
            if (ddl.isEmpty()) {
                continue;
            }
            try (Statement statement = connection.createStatement()) {
                statement.execute(ddl);
            }
        }
    }

    static List<Document> loadDocuments(String resourcePath) throws IOException {
        try (InputStream stream = HybridSearchSample.class.getResourceAsStream(resourcePath)) {
            if (stream == null) {
                throw new IOException("Document resource not found: " + resourcePath);
            }
            try (Reader reader = new InputStreamReader(stream, StandardCharsets.UTF_8);
                 JsonReader jsonReader = Json.createReader(reader)) {
                JsonArray array = jsonReader.readArray();
                List<Document> documents = new ArrayList<>();
                for (int i = 0; i < array.size(); i++) {
                    JsonObject object = array.getJsonObject(i);
                    documents.add(new Document(
                            object.getString("title"),
                            object.getString("content"),
                            object.getString("category"),
                            object.getJsonNumber("price").doubleValue(),
                            object.getJsonObject("metadata").toString()
                    ));
                }
                return documents;
            }
        }
    }

    static void seedSampleData(Connection connection, List<Document> documents) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(INSERT_SQL)) {
            for (Document document : documents) {
                statement.setString(1, document.title());
                statement.setString(2, document.content());
                statement.setString(3, document.category());
                statement.setDouble(4, document.price());
                statement.setString(5, document.metadata());
                statement.setObject(6, VectorUtil.embedToFloat32VECTOR(document.content()));
                statement.addBatch();
            }
            statement.executeBatch();
        }
    }

    static String readResource(String resourcePath) throws IOException {
        try (InputStream stream = HybridSearchSample.class.getResourceAsStream(resourcePath)) {
            if (stream == null) {
                throw new IOException("Resource not found: " + resourcePath);
            }
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
