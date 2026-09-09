package com.example.news;


import java.net.URI;
import java.sql.SQLException;
import java.util.List;

import com.example.news.events.producerconsumer.RawNewsProducer;
import com.example.news.genai.vectorstore.NewsQueryService;
import com.example.news.model.NewsDTO;
import com.example.news.model.SearchRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@RestController
public class NewsService {
    private final RawNewsProducer rawNewsProducer;
    private final NewsQueryService newsQueryService;

    public NewsService(RawNewsProducer rawNewsProducer, NewsQueryService newsQueryService) {
        this.rawNewsProducer = rawNewsProducer;
        this.newsQueryService = newsQueryService;
    }


    @PostMapping("/news")
    public ResponseEntity<?> postNews(@RequestBody List<String> news) throws SQLException {
        rawNewsProducer.send(news);
        return ResponseEntity.created(location()).build();
    }

    @GetMapping("/news")
    public ResponseEntity<SearchResponse> getNews(@RequestBody SearchRequest searchRequest) throws Exception {
        List<NewsDTO> results = newsQueryService.search(searchRequest);
        if (results.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(new SearchResponse(results));
    }

    @PostMapping("/news/summarize")
    public ResponseEntity<SummarizeResponse> summarize(@RequestBody SearchRequest searchRequest) throws Exception {
        return ResponseEntity.ok(new SummarizeResponse(newsQueryService.summarize(searchRequest)));
    }

    @PostMapping("/news/summarize/{id}")
    public ResponseEntity<SummarizeResponse> summarizeById(@PathVariable("id") String id) throws Exception {
        return ResponseEntity.ok(new SummarizeResponse(newsQueryService.summarize(id)));
    }

    @PostMapping("/news/reset")
    public ResponseEntity<?> resetNews() throws Exception {
        newsQueryService.cleanup();
        return ResponseEntity.noContent().build();
    }

    public record SummarizeResponse(String result) {}

    public record SearchResponse(List<NewsDTO> articles) {
    }

    private URI location() {
        return ServletUriComponentsBuilder
                .fromCurrentRequest()
                .build()
                .toUri();
    }
}
