package com.example.news.events.producerconsumer;

import java.util.List;

import org.apache.kafka.clients.producer.ProducerRecord;
import org.oracle.okafka.clients.producer.KafkaProducer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class RawNewsProducer implements AutoCloseable {
    private static final Logger log = LoggerFactory.getLogger(RawNewsProducer.class);

    private final String rawTopic;
    private final KafkaProducer<String, String> producer;


    public RawNewsProducer(
            String rawTopic,
            KafkaProducer<String, String> producer) {
        this.rawTopic = rawTopic;
        this.producer = producer;
    }

    public void send(List<String> news) {
        try {
            news.parallelStream().forEach(newsItem -> {
                ProducerRecord<String, String> record = new ProducerRecord<>(rawTopic, newsItem);
                producer.send(record);
            });
            log.info("Successfully produced {} records", news.size());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public void close() throws Exception {
        this.producer.close();
    }
}
