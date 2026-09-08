package com.example.news.events.parser;

import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

import com.example.news.model.News;
import com.example.news.genai.embedding.EmbeddingService;
import com.example.news.model.NewsVector;
import oracle.sql.VECTOR;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

@Component
public class Parser {
    private final EmbeddingService embeddingService;
    private final Splitter splitter;

    public Parser(EmbeddingService embeddingService,
                  Splitter splitter) {
        this.embeddingService = embeddingService;
        this.splitter = splitter;
    }

    @Async
    public CompletableFuture<News> parseAsync(String text) throws SQLException {
        News news = new News();
        news.setArticle(text);
        List<String> chunks = splitter.split(news.getArticle());
        List<VECTOR> vectors = embeddingService.embedAll(chunks);

        List<NewsVector> embeddings = new ArrayList<>();
        for (int i = 0; i < vectors.size(); i++) {
            NewsVector newsVector = new NewsVector();
            newsVector.setEmbedding(vectors.get(i).toFloatArray());
            newsVector.setChunk(chunks.get(i));
            embeddings.add(newsVector);
        }

        news.setNews_vector(embeddings);
        return CompletableFuture.completedFuture(news);
    }
}
