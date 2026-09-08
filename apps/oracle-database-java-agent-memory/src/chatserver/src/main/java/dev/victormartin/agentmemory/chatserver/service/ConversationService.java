package dev.victormartin.agentmemory.chatserver.service;

import java.util.List;

import dev.victormartin.agentmemory.chatserver.model.ConversationSummary;
import dev.victormartin.agentmemory.chatserver.repository.ConversationSummaryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class ConversationService {

    private static final Logger log = LoggerFactory.getLogger(ConversationService.class);

    private final JdbcTemplate jdbcTemplate;
    private final ConversationSummaryRepository summaryRepository;
    private final ChatModel chatModel;

    public ConversationService(JdbcTemplate jdbcTemplate,
                               ConversationSummaryRepository summaryRepository,
                               ChatModel chatModel) {
        this.jdbcTemplate = jdbcTemplate;
        this.summaryRepository = summaryRepository;
        this.chatModel = chatModel;
    }

    public List<ConversationInfo> listConversations() {
        return jdbcTemplate.query("""
                SELECT m.CONVERSATION_ID, s.SUMMARY, MAX(m."TIMESTAMP") AS LAST_ACTIVE
                FROM SPRING_AI_CHAT_MEMORY m
                LEFT JOIN CONVERSATION_SUMMARY s ON m.CONVERSATION_ID = s.CONVERSATION_ID
                GROUP BY m.CONVERSATION_ID, s.SUMMARY
                ORDER BY LAST_ACTIVE DESC
                """,
                (rs, rowNum) -> new ConversationInfo(
                        rs.getString("CONVERSATION_ID"),
                        rs.getString("SUMMARY"),
                        rs.getTimestamp("LAST_ACTIVE").toLocalDateTime().toString()
                ));
    }

    public List<MessageDto> getMessages(String conversationId) {
        return jdbcTemplate.query("""
                SELECT "TYPE", CONTENT FROM SPRING_AI_CHAT_MEMORY
                WHERE CONVERSATION_ID = ? AND "TYPE" IN ('USER', 'ASSISTANT')
                ORDER BY "TIMESTAMP"
                """,
                (rs, rowNum) -> new MessageDto(
                        rs.getString("TYPE").toLowerCase(),
                        rs.getString("CONTENT")
                ),
                conversationId);
    }

    public void generateSummaryIfNeeded(String conversationId, String userMessage) {
        if (summaryRepository.existsById(conversationId)) {
            return;
        }
        try {
            String summaryPrompt = "Summarize this message topic in exactly 2 to 4 words. " +
                    "Reply with ONLY the summary, nothing else. No quotes, no punctuation: " + userMessage;
            String summary = chatModel.call(new Prompt(summaryPrompt))
                    .getResult().getOutput().getText().trim();
            if (summary.length() > 50) {
                summary = summary.substring(0, 50);
            }
            summaryRepository.save(new ConversationSummary(conversationId, summary));
            log.info("[conv:{}] Generated summary: \"{}\"", conversationId, summary);
        } catch (Exception e) {
            log.warn("[conv:{}] Failed to generate summary", conversationId, e);
        }
    }
}
