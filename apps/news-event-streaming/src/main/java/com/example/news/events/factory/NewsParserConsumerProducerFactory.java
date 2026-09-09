package com.example.news.events.factory;

import java.sql.Connection;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import com.example.news.events.producerconsumer.NewsParserConsumerProducer;
import com.example.news.events.producerconsumer.OKafkaTask;
import com.example.news.model.News;
import com.example.news.events.parser.Parser;
import com.example.news.events.serde.JSONBSerializer;
import com.oracle.spring.json.jsonb.JSONB;
import org.apache.kafka.common.serialization.Serializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.oracle.okafka.clients.consumer.KafkaConsumer;
import org.oracle.okafka.clients.producer.KafkaProducer;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class NewsParserConsumerProducerFactory {
    private final Properties okafkaProperties;
    private final JSONB jsonb;
    private final Parser parser;
    private final String rawTopic;
    private final String parsedTopic;
    private final int numThreads;

    public NewsParserConsumerProducerFactory(@Qualifier("okafkaProperties") Properties okafkaProperties,
                                             JSONB jsonb,
                                             Parser parser,
                                             @Value("${news.topic.raw}") String rawTopic,
                                             @Value("${news.topic.parsed}") String parsedTopic,
                                             @Value("${news.threads.newsParserConsumerProducer}") int numThreads) {
        this.okafkaProperties = okafkaProperties;
        this.jsonb = jsonb;
        this.parser = parser;
        this.rawTopic = rawTopic;
        this.parsedTopic = parsedTopic;
        this.numThreads = numThreads;
    }

    public List<OKafkaTask> create() {
        List<OKafkaTask> tasks = new ArrayList<>();
        for (int i = 0; i < numThreads; i++) {
            KafkaConsumer<String, String> consumer = createConsumer();
            NewsParserConsumerProducer consumerProducer = new NewsParserConsumerProducer(
                    consumer,
                    createProducer(consumer.getDBConnection()),
                    parser,
                    rawTopic,
                    parsedTopic
            );
            tasks.add(consumerProducer);
        }
        return tasks;
    }

    private KafkaConsumer<String, String> createConsumer() {
        Properties props = new Properties();
        props.putAll(okafkaProperties);
        // Note the use of standard Kafka properties for OKafka configuration.
        props.put("group.id" , "RAW_NEWS_CONSUMER");
        props.put("enable.auto.commit","false");
        props.put("max.poll.records", 50);
        props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("auto.offset.reset", "earliest");

        return new KafkaConsumer<>(props);
    }

    private KafkaProducer<String, News> createProducer(Connection connection) {
        Properties props = new Properties();
        props.putAll(okafkaProperties);
        props.put("enable.idempotence", "true");
        // This property is required for transactional producers
        props.put("oracle.transactional.producer", "true");

        Serializer<String> keySerializer = new StringSerializer();
        Serializer<News> valueSerializer = new JSONBSerializer<>(jsonb);
        KafkaProducer<String, News> producer = new KafkaProducer<>(props, keySerializer, valueSerializer, connection);
        producer.initTransactions();
        return producer;
    }
}
