package com.example.hybrid;

import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.embedding.onnx.allminilml6v2.AllMiniLmL6V2EmbeddingModel;
import oracle.sql.VECTOR;

import java.sql.SQLException;

public final class VectorUtil {
    private static final EmbeddingModel EMBEDDING_MODEL = new AllMiniLmL6V2EmbeddingModel();

    static VECTOR embedToFloat32VECTOR(String text) throws SQLException {
        return toOracleVector(embeddingForText(text));
    }

    private static float[] embeddingForText(String text) {
        return EMBEDDING_MODEL.embed(text).content().vector();
    }

    private static VECTOR toOracleVector(float[] vector) throws SQLException {
        return VECTOR.ofFloat32Values(normalize(vector));
    }

    // Normalize once before writing so database similarity and sample math stay aligned.
    private static float[] normalize(float[] vector) {
        float[] copy = vector.clone();
        double squaredSum = 0d;
        for (float value : copy) {
            squaredSum += value * value;
        }

        double magnitude = Math.sqrt(squaredSum);
        if (magnitude == 0d) {
            return copy;
        }

        for (int i = 0; i < copy.length; i++) {
            copy[i] /= (float) magnitude;
        }
        return copy;
    }
}
