package com.example.news.events.producerconsumer;

import java.sql.SQLException;
import java.time.Duration;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicBoolean;

import com.example.news.genai.vectorstore.NewsStore;
import com.example.news.model.News;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.oracle.okafka.clients.consumer.KafkaConsumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;

public class NewsConsumer implements OKafkaTask {
    private static final Logger log = LoggerFactory.getLogger(NewsConsumer.class);

    private final KafkaConsumer<String, News> consumer;
    private final String newsTopic;
    private final NewsStore vectorStore;
    private final AtomicBoolean running = new AtomicBoolean(true);


    public NewsConsumer(KafkaConsumer<String, News> consumer,
                        @Value("${news.topic.parsed}") String newsTopic, NewsStore vectorStore) {
        this.consumer = consumer;
        this.newsTopic = newsTopic;
        this.vectorStore = vectorStore;
    }


    @Override
    public void run() {
        if (!running.get()) {
            return;
        }
        consumer.subscribe(Collections.singletonList(newsTopic));

        while (running.get()) {
            // Poll a batch of records from the news topic.
            ConsumerRecords<String, News> records = consumer.poll(Duration.ofMillis(200));
            if (records.isEmpty()) {
                continue;
            }
            try {
                // Add all news records to the
                vectorStore.addAll(records, consumer.getDBConnection());
                // You may also use auto-commit, or consumer.commitAsync()
                consumer.commitSync();
                log.info("Committed {} records", records.count());
            } catch (Exception e) {
                log.error("Error processing news events", e);
                handleError();
            }
        }
        this.consumer.close();
    }

    private void handleError() {
        try {
            consumer.getDBConnection().rollback();
        } catch (SQLException e) {
            log.error("Error rolling back transaction", e);
        }

    }

    @Override
    public void close() throws Exception {
        running.set(false);
    }
}
