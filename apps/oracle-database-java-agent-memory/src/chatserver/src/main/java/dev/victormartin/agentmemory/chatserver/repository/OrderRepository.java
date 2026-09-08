package dev.victormartin.agentmemory.chatserver.repository;

import java.util.Optional;

import dev.victormartin.agentmemory.chatserver.model.CustomerOrder;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<CustomerOrder, String> {
    Optional<CustomerOrder> findByOrderId(String orderId);
}
