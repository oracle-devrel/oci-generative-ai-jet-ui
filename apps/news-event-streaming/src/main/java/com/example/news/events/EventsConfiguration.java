package com.example.news.events;

import java.util.Properties;

import com.example.news.events.producerconsumer.RawNewsProducer;
import org.oracle.okafka.clients.producer.KafkaProducer;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class EventsConfiguration {
    @Value("${okafka.ojdbcPath}")
    private String ojdbcPath;

    @Value("${okafka.bootstrapServers:localhost:1521}")
    private String bootstrapServers;

    // We use the default 26ai Free service name
    @Value("${okafka.serviceName:freepdb1}")
    private String serviceName;

    // We use plaintext for a containerized, local database.
    // Use "SSL" for wallet connections, like Autonomous Database.
    @Value("${okafka.securityProtocol:PLAINTEXT}")
    private String securityProtocol;

    @Value("${news.topic.raw}")
    private String rawTopic;

    @Bean
    @Qualifier("stringProducer")
    public KafkaProducer<String, String> stringProducer() {
        Properties props = okafkaProperties();
        props.put("enable.idempotence", "true");
        props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        // Note the use of the org.oracle.okafka.clients.producer.KafkaProducer class
        // for producing records to Oracle AI Database Transactional Event Queues.
        KafkaProducer<String, String> stringProducer = new KafkaProducer<>(props);
        return stringProducer;
    }

    @Bean
    public RawNewsProducer rawNewsProducer(@Qualifier("stringProducer") KafkaProducer<String, String> stringProducer) {
        return new RawNewsProducer(rawTopic, stringProducer);
    }

    @Bean
    @Qualifier("okafkaProperties")
    public Properties okafkaProperties() {
        Properties props = new Properties();
        props.put("oracle.service.name", serviceName);
        props.put("security.protocol", securityProtocol);
        props.put("bootstrap.servers", bootstrapServers);
        // If using Oracle AI Database wallet, pass wallet directory
        props.put("oracle.net.tns_admin", ojdbcPath);
        return props;
    }
}
