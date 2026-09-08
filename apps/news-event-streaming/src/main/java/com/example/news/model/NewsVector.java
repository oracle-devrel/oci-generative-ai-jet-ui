package com.example.news.model;

import java.util.Arrays;
import java.util.Objects;
import java.util.UUID;

public class NewsVector {
    private String id = UUID.randomUUID().toString();
    private String chunk;
    private float[] embedding;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getChunk() {
        return chunk;
    }

    public void setChunk(String chunk) {
        this.chunk = chunk;
    }

    public float[] getEmbedding() {
        return embedding;
    }

    public void setEmbedding(float[] embedding) {
        this.embedding = embedding;
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        NewsVector that = (NewsVector) o;
        return Objects.equals(id, that.id) && Objects.equals(chunk, that.chunk) && Objects.deepEquals(embedding, that.embedding);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, chunk, Arrays.hashCode(embedding));
    }
}
