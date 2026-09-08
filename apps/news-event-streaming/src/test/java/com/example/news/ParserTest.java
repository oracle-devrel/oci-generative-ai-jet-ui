package com.example.news;

import com.example.news.events.parser.Parser;
import com.example.news.events.parser.ParserConfiguration;
import com.example.news.events.parser.Splitter;
import com.example.news.genai.GenAIConfiguration;
import com.example.news.genai.embedding.OCIEmbeddingService;
import com.example.news.genai.vectorstore.VectorDataAdapter;
import com.example.news.model.News;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static com.example.news.Utils.readFile;
import static org.assertj.core.api.Assertions.assertThat;


@SpringBootTest(classes = {
        Parser.class,
        OCIEmbeddingService.class,
        Splitter.class,
        VectorDataAdapter.class,
        ParserConfiguration.class,
        GenAIConfiguration.class
})
// This integration test uses OCI GenAI services.
// To run this test, set the following environment variables using your OCI compartment,
// and Cohere model IDs for chat and embedding.
@EnabledIfEnvironmentVariable(named = "OCI_COMPARTMENT", matches = ".+")
@EnabledIfEnvironmentVariable(named = "OCI_EMBEDDING_MODEL_ID", matches = ".+")
public class ParserTest {

    @Autowired
    private Parser parser;

    @Test
    void parseArticles() throws Exception {
        String s = readFile("one-record.json");
        News news = parser.parseAsync(s.substring(1, s.length()-1)).get();
        assertThat(news).isNotNull();
        assertThat(news.getNews_vector().size()).isGreaterThan(1);
    }
}
