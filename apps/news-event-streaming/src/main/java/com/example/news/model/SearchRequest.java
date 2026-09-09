package com.example.news.model;

import java.util.Objects;

public record SearchRequest(String input,
                            Double minScore) {

    public Double getMinScore() {
        return Objects.requireNonNullElse(minScore, 0.5);
    }
}
