package com.example.news.genai.embedding;

import java.util.Collections;
import java.util.List;

import oracle.sql.VECTOR;

public interface EmbeddingService {
    List<VECTOR> embedAll(List<String> chunks);
    default VECTOR embed(String chunk) {
        return embedAll(Collections.singletonList(chunk)).getFirst();
    }
}
