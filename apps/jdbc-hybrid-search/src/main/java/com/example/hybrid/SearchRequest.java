package com.example.hybrid;

public record SearchRequest(
        String text,
        String category,
        double maxPrice,
        String audience,
        String topic,
        int maxResults,
        double minScore
) {
}
