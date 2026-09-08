package com.example.news.genai.vectorstore;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

import com.example.news.genai.chat.ChatService;
import com.example.news.genai.embedding.EmbeddingService;
import com.example.news.model.NewsDTO;
import com.example.news.model.SearchRequest;
import javax.sql.DataSource;
import oracle.sql.VECTOR;
import org.springframework.stereotype.Component;

@Component
public class NewsQueryService {
    private final NewsStore newsStore;
    private final EmbeddingService embeddingService;
    private final ChatService chatService;
    private final DataSource dataSource;

    private static final String summaryTemplate = """
            You are an assistant for summarizing news articles.
            Summarize the the following retrieved news article, and do not use any outside information.
            Use one paragraph maximum and keep the answer concise without extra detail.
            Article to summarize: {%s}
            Summary:
            """;

    private static final String notFoundMessage = "I'm sorry, but I couldn't find any relevant articles for the given query.";

    public NewsQueryService(NewsStore newsStore, EmbeddingService embeddingService, ChatService chatService, DataSource dataSource) {
        this.newsStore = newsStore;
        this.embeddingService = embeddingService;
        this.chatService = chatService;
        this.dataSource = dataSource;
    }

    public List<NewsDTO> search(SearchRequest searchRequest) throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            VECTOR vector = embeddingService.embed(searchRequest.input());

            return newsStore.search(
                    searchRequest,
                    vector,
                    conn
            );
        }
    }

    public String summarize(SearchRequest summarizeRequest) throws SQLException {
        List<NewsDTO> results = search(summarizeRequest);
        return summarize(results.stream().findFirst());
    }

    public String summarize(String id) throws SQLException {
        try (Connection conn = dataSource.getConnection()){
            return summarize(newsStore.findByID(id, conn));
        }
    }

    private String summarize(Optional<NewsDTO> newsDTO) {
        return newsDTO.map(news -> chatService.chat(summaryTemplate.formatted(news.article())))
                .orElse(notFoundMessage);
    }

    public void cleanup() throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            newsStore.cleanup(conn);
        }
    }


}
