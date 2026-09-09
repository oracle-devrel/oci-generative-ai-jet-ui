package com.example.hybrid;

public record SearchResult(
        long id,
        String title,
        String category,
        double price,
        String audience,
        double score
) {
}
