package com.example.news.events;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.atomic.AtomicBoolean;

import com.example.news.events.factory.NewsConsumerFactory;
import com.example.news.events.factory.NewsParserConsumerProducerFactory;
import com.example.news.events.producerconsumer.OKafkaTask;
import jakarta.annotation.PostConstruct;
import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.errors.TopicExistsException;
import org.oracle.okafka.clients.admin.AdminClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.stereotype.Component;

/**
 * The OKafkaManager creates the "raw" and "parsed" news topics on application startup.
 * If the topics already exist, a message is logged.
 * Additionally, the OKafkaManager starts consumer threads on application startup.
 */
@Component
public class OKafkaManager implements AutoCloseable {
    private static final Logger log = LoggerFactory.getLogger(OKafkaManager.class);

    private final AsyncTaskExecutor asyncTaskExecutor;
    private final Properties okafkaProperties;
    private final String rawTopic;
    private final String parsedTopic;
    private final List<OKafkaTask> okafkaTasks = new ArrayList<>();
    private final AtomicBoolean closed = new AtomicBoolean();

    private final NewsParserConsumerProducerFactory newsParserConsumerProducerFactory;
    private final NewsConsumerFactory newsConsumerFactory;

    public OKafkaManager(@Qualifier("applicationTaskExecutor") AsyncTaskExecutor asyncTaskExecutor,
                         @Qualifier("okafkaProperties") Properties okafkaProperties,
                         @Value("${news.topic.raw}") String rawTopic,
                         @Value("${news.topic.parsed}") String parsedTopic,
                         NewsParserConsumerProducerFactory newsParserConsumerProducerFactory,
                         NewsConsumerFactory newsConsumerFactory) {
        this.asyncTaskExecutor = asyncTaskExecutor;
        this.okafkaProperties = okafkaProperties;
        this.rawTopic = rawTopic;
        this.parsedTopic = parsedTopic;
        this.newsParserConsumerProducerFactory = newsParserConsumerProducerFactory;
        this.newsConsumerFactory = newsConsumerFactory;
    }

    @PostConstruct
    public void init() {
        try (Admin admin = AdminClient.create(okafkaProperties)) {
            createTopicIfNotExists(admin, new NewTopic(rawTopic, 1, (short) 1));
            createTopicIfNotExists(admin, new NewTopic(parsedTopic, 1, (short) 1));
        }

        submit(newsParserConsumerProducerFactory.create());
        submit(newsConsumerFactory.create());
    }

    private void submit(List<OKafkaTask> tasks) {
        okafkaTasks.addAll(tasks);
        for (OKafkaTask task : tasks) {
            asyncTaskExecutor.execute(task);
        }
    }

    private void createTopicIfNotExists(Admin admin, NewTopic newTopic) {
        try {
            admin.createTopics(Collections.singletonList(newTopic))
                    .all()
                    .get();
        } catch (ExecutionException | InterruptedException e) {
            if (e.getCause() instanceof TopicExistsException) {
                log.info("Topic {} already exists, skipping creation", newTopic);
            } else {
                throw new RuntimeException(e);
            }
        }
    }

    @Override
    public void close() throws Exception {
        if (!closed.compareAndSet(false, true)) {
            return;
        }
        for (OKafkaTask task : okafkaTasks) {
            task.close();
        }
    }
}
