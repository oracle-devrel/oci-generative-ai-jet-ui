package com.example.news.genai.vectorstore;

import java.sql.SQLException;
import java.util.List;

import oracle.sql.VECTOR;
import org.springframework.stereotype.Component;

@Component
public class VectorDataAdapter {
    public VECTOR toVECTOR(List<Float> e) throws SQLException {
        double[] vector = e.stream()
                .mapToDouble(Float::floatValue)
                .toArray();
        return VECTOR.ofFloat64Values(vector);
    }

    /**
     * Normalizes a vector, converting it to a unit vector with length 1.
     * @param v Vector to normalize.
     * @return The normalized vector.
     */
    private float[] normalize(float[] v) {
        double squaredSum = 0d;

        for (float e : v) {
            squaredSum += e * e;
        }

        final float magnitude = (float) Math.sqrt(squaredSum);

        if (magnitude > 0) {
            final float multiplier = 1f / magnitude;
            final int length = v.length;
            for (int i = 0; i < length; i++) {
                v[i] *= multiplier;
            }
        }

        return v;
    }
}
