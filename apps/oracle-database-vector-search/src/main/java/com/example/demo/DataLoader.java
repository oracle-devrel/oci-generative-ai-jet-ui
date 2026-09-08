package com.example.demo;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
public class DataLoader implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DataLoader.class);
    private final VectorStore vectorStore;

    public DataLoader(VectorStore vectorStore) {
        this.vectorStore = vectorStore;
    }

    @Override
    public void run(ApplicationArguments args) {
        log.info("Loading initial pet inventory data...");

        List<Document> inventory = List.of(
                new Document("Labrador Bark Control Chews", Map.of("price", 15, "type", "health", "animal", "dog")),
                new Document("Heavy Duty Rope for Large Dog Breeds",
                        Map.of("price", 12, "type", "toy", "animal", "dog")),
                new Document("Silent Laser Pointer for Kittens", Map.of("price", 8, "type", "toy", "animal", "cat")),
                new Document("Hair brush for Long Hair Cats", Map.of("price", 5, "type", "tool", "animal", "cat")),
                new Document("Fish Tank for Small Fish", Map.of("price", 48, "type", "habitat", "animal", "fish")),
                new Document("Gourmet Tuna Soufflé for Sphynx Cats",
                        Map.of("price", 18, "type", "food", "animal", "cat")),
                new Document("Gourmet Chicken Soup for Senior Cats",
                        Map.of("price", 12, "type", "food", "animal", "cat")));

        vectorStore.add(inventory);

        inventory.forEach(doc -> log.info("Successfully loaded item '{}', ${}, {}, into vector store",
                doc.getText(),
                doc.getMetadata().get("price"),
                doc.getMetadata().get("type")));

        log.info("Successfully loaded {} products into vector store", inventory.size());
    }
}
