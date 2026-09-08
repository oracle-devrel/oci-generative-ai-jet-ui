package dev.victormartin.agentmemory.chatserver.repository;

import dev.victormartin.agentmemory.chatserver.model.ConversationSummary;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ConversationSummaryRepository extends JpaRepository<ConversationSummary, String> {
}
