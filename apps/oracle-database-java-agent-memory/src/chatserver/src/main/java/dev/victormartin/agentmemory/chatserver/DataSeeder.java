package dev.victormartin.agentmemory.chatserver;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.victormartin.agentmemory.chatserver.model.CustomerOrder;
import dev.victormartin.agentmemory.chatserver.model.OrderStatus;
import dev.victormartin.agentmemory.chatserver.repository.OrderRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class DataSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataSeeder.class);

    private final OrderRepository orderRepository;
    private final JdbcTemplate jdbcTemplate;

    public DataSeeder(OrderRepository orderRepository, JdbcTemplate jdbcTemplate) {
        this.orderRepository = orderRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public void run(String... args) throws Exception {
        seedOrders();
        seedPolicies();
    }

    private void seedOrders() {
        if (orderRepository.count() > 0) {
            log.info("Orders already seeded, skipping.");
            return;
        }

        LocalDate today = LocalDate.now();

        List<CustomerOrder> orders = List.of(
                new CustomerOrder("ORD-1001", "Wireless Headphones", 1, new BigDecimal("79.99"),
                        OrderStatus.DELIVERED, today.minusDays(10), "123 Main St, Springfield"),
                new CustomerOrder("ORD-1002", "USB-C Hub", 1, new BigDecimal("45.00"),
                        OrderStatus.SHIPPED, today.minusDays(3), "123 Main St, Springfield"),
                new CustomerOrder("ORD-1003", "Mechanical Keyboard", 1, new BigDecimal("129.99"),
                        OrderStatus.DELIVERED, today.minusDays(45), "123 Main St, Springfield"),
                new CustomerOrder("ORD-1004", "Monitor Stand", 2, new BigDecimal("34.50"),
                        OrderStatus.PLACED, today, "456 Oak Ave, Shelbyville"),
                new CustomerOrder("ORD-1005", "Laptop Sleeve", 1, new BigDecimal("25.99"),
                        OrderStatus.DELIVERED, today.minusDays(20), "456 Oak Ave, Shelbyville"),
                new CustomerOrder("ORD-1006", "Webcam HD", 1, new BigDecimal("59.99"),
                        OrderStatus.CONFIRMED, today.minusDays(1), "123 Main St, Springfield"),
                new CustomerOrder("ORD-1007", "Bluetooth Speaker", 1, new BigDecimal("89.99"),
                        OrderStatus.CANCELLED, today.minusDays(15), "789 Elm Dr, Capital City"),
                new CustomerOrder("ORD-1008", "Ergonomic Mouse", 1, new BigDecimal("39.99"),
                        OrderStatus.DELIVERED, today.minusDays(5), "789 Elm Dr, Capital City")
        );

        orderRepository.saveAll(orders);
        log.info("Seeded {} demo orders.", orders.size());
    }

    private void seedPolicies() throws Exception {
        Integer count = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM POLICY_DOCS", Integer.class);
        if (count != null && count > 0) {
            log.info("Policies already seeded, skipping.");
            return;
        }

        log.info("Seeding policy documents into POLICY_DOCS...");

        ObjectMapper mapper = new ObjectMapper();
        List<String> texts = mapper.readValue(
                new ClassPathResource("policies.json").getInputStream(),
                new TypeReference<>() {}
        );

        for (String text : texts) {
            jdbcTemplate.update(
                    "INSERT INTO POLICY_DOCS (id, content) VALUES (sys_guid(), ?)",
                    text);
        }
        log.info("Seeded {} policy documents.", texts.size());
    }
}
