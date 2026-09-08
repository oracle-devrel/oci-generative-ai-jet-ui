package dev.victormartin.agentmemory.chatserver.model;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "CONVERSATION_SUMMARY")
public class ConversationSummary {

    @Id
    @Column(name = "CONVERSATION_ID")
    private String conversationId;

    @Column(name = "SUMMARY", nullable = false)
    private String summary;

    @Column(name = "CREATED_AT", nullable = false)
    private LocalDateTime createdAt;

    public ConversationSummary() {}

    public ConversationSummary(String conversationId, String summary) {
        this.conversationId = conversationId;
        this.summary = summary;
        this.createdAt = LocalDateTime.now();
    }

    public String getConversationId() { return conversationId; }
    public void setConversationId(String conversationId) { this.conversationId = conversationId; }

    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
