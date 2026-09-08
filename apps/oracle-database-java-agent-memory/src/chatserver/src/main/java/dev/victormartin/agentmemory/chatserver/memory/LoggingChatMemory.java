package dev.victormartin.agentmemory.chatserver.memory;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.messages.Message;

public class LoggingChatMemory implements ChatMemory {

    private static final Logger log = LoggerFactory.getLogger(LoggingChatMemory.class);

    private final ChatMemory delegate;

    public LoggingChatMemory(ChatMemory delegate) {
        this.delegate = delegate;
    }

    @Override
    public void add(String conversationId, List<Message> messages) {
        log.info("[EPISODIC] Saving {} message(s) to conversation {}", messages.size(), conversationId);
        delegate.add(conversationId, messages);
    }

    @Override
    public List<Message> get(String conversationId) {
        List<Message> messages = delegate.get(conversationId);
        log.info("[EPISODIC] Loaded {} message(s) from conversation {}", messages.size(), conversationId);
        return messages;
    }

    @Override
    public void clear(String conversationId) {
        log.info("[EPISODIC] Clearing conversation {}", conversationId);
        delegate.clear(conversationId);
    }
}
