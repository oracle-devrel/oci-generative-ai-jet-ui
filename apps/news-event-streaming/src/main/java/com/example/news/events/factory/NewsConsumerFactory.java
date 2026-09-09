package com.example.news.events.factory;

import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import com.example.news.events.producerconsumer.NewsConsumer;
import com.example.news.events.producerconsumer.OKafkaTask;
import com.example.news.genai.vectorstore.NewsStore;
import com.example.news.model.News;
import com.example.news.events.serde.JSONBDeserializer;
import com.oracle.spring.json.jsonb.JSONB;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.oracle.okafka.clients.consumer.KafkaConsumer;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class NewsConsumerFactory {
    private final Properties okafkaProperties;
    private final NewsStore newsStore;
    private final JSONB jsonb;
    private final String parsedTopic;
    private final int numThreads;

    public NewsConsumerFactory(@Qualifier("okafkaProperties") Properties okafkaProperties,
                               NewsStore newsStore,
                               JSONB jsonb,
                               @Value("${news.topic.parsed}") String parsedTopic,
                               @Value("${news.threads.newsParserConsumerProducer}") int numThreads) {
        this.okafkaProperties = okafkaProperties;
        this.newsStore = newsStore;
        this.jsonb = jsonb;
        this.parsedTopic = parsedTopic;
        this.numThreads = numThreads;
    }

    public List<OKafkaTask> create() {
        List<OKafkaTask> tasks = new ArrayList<>();
        for (int i = 0; i < numThreads; i++) {
            NewsConsumer newsConsumer = new NewsConsumer(
                    createConsumer(),
                    parsedTopic,
                    newsStore
            );
            tasks.add(newsConsumer);
        }
        return tasks;
    }

    public KafkaConsumer<String, News> createConsumer() {
        Properties props = new Properties();
        props.putAll(okafkaProperties);
        props.put("auto.offset.reset", "earliest");
        props.put("group.id" , "NEWS_CONSUMER");
        props.put("enable.auto.commit","false");
        props.put("max.poll.records", 50);

        Deserializer<String> keyDeserializer = new StringDeserializer();
        Deserializer<News> valueDeserializer = new JSONBDeserializer<>(jsonb, News.class);
        return new KafkaConsumer<>(props, keyDeserializer, valueDeserializer);
    }
}
