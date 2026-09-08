package dev.victormartin.agentmemory.chatserver.repository;

import dev.victormartin.agentmemory.chatserver.model.SupportTicket;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SupportTicketRepository extends JpaRepository<SupportTicket, Long> {
}
