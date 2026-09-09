package com.example.news;

import com.example.news.events.OKafkaManager;
import com.example.news.events.producerconsumer.RawNewsProducer;
import com.example.news.model.SearchRequest;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.oracle.OracleContainer;
import org.testcontainers.utility.MountableFile;

import static com.example.news.Utils.readFile;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
// This integration test uses OCI GenAI services.
// To run this test, set the following environment variables using your OCI compartment,
// and Cohere model IDs for chat and embedding.
@EnabledIfEnvironmentVariable(named = "OCI_COMPARTMENT", matches = ".+")
@EnabledIfEnvironmentVariable(named = "OCI_CHAT_MODEL_ID", matches = ".+")
@EnabledIfEnvironmentVariable(named = "OCI_EMBEDDING_MODEL_ID", matches = ".+")
@EnabledIfEnvironmentVariable(named = "OJDBC_PATH", matches = ".+")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public class NewsEventStreamingIT {
    // Pre-pull this image to avoid testcontainers image pull timeouts:
    // docker pull gvenzl/oracle-free:23.26.3-slim-faststart
    @Container
    @ServiceConnection
    private static final OracleContainer oracleContainer = new OracleContainer("gvenzl/oracle-free:23.26.3-slim-faststart")
            .withUsername("testuser")
            .withPassword("testpwd")
            .withInitScript("news-schema.sql");

    static {
        oracleContainer.start();
        oracleContainer.copyFileToContainer(MountableFile.forClasspathResource("testuser.sql"), "/tmp/user.sql");
        try {
            oracleContainer.execInContainer("sqlplus", "sys / as sysdba", "@/tmp/user.sql");
        } catch (IOException | InterruptedException e) {
            throw new RuntimeException(e);
        }
    }

    @DynamicPropertySource
    static void setProperties(DynamicPropertyRegistry registry) {
        registry.add("okafka.bootstrapServers", () -> "localhost:" + oracleContainer.getOraclePort());
    }

    @Autowired
    NewsService newsService;

    @Autowired
    OKafkaManager okafkaManager;

    @Autowired
    RawNewsProducer rawNewsProducer;

    @Test
    public void newsWorkflow() throws Exception {
        String s = readFile("one-record.json");
        List<String> article = new ObjectMapper().readValue(s, new TypeReference<>() {});
        ResponseEntity<?> resp = newsService.postNews(article);
        assertThat(resp.getStatusCode().is2xxSuccessful()).isTrue();


        Thread.sleep(20000);
        ResponseEntity<NewsService.SearchResponse> resp2 = newsService.getNews(new SearchRequest(
                "Large Hadron Collider particle accelerator",
                0.2
        ));
        assertThat(resp2.getStatusCode().is2xxSuccessful()).isTrue();

        assertThat(resp2.getBody()).isNotNull();
        assertThat(resp2.getBody().articles()).isNotEmpty();
        String id = resp2.getBody().articles().getFirst().id();

        ResponseEntity<NewsService.SummarizeResponse> resp3 = newsService.summarizeById(id);
        assertThat(resp3.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(resp3.getBody()).isNotNull();
        assertThat(resp3.getBody().result()).isNotEmpty();

        okafkaManager.close();
        rawNewsProducer.close();
    }
}
