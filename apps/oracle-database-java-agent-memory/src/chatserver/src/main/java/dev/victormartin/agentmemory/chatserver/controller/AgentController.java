package dev.victormartin.agentmemory.chatserver.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.memory.MessageWindowChatMemory;
import org.springframework.ai.chat.memory.repository.jdbc.JdbcChatMemoryRepository;
import org.springframework.ai.chat.prompt.PromptTemplate;
import org.springframework.ai.rag.advisor.RetrievalAugmentationAdvisor;
import org.springframework.ai.rag.generation.augmentation.ContextualQueryAugmenter;
import org.springframework.jdbc.core.JdbcTemplate;

import dev.victormartin.agentmemory.chatserver.memory.LoggingChatMemory;
import dev.victormartin.agentmemory.chatserver.retriever.OracleHybridDocumentRetriever;
import dev.victormartin.agentmemory.chatserver.service.ConversationInfo;
import dev.victormartin.agentmemory.chatserver.service.ConversationService;
import dev.victormartin.agentmemory.chatserver.service.MessageDto;
import dev.victormartin.agentmemory.chatserver.tools.AgentTools;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/agent")
public class AgentController {

    private static final Logger log = LoggerFactory.getLogger(AgentController.class);
    private static final int MAX_MESSAGE_LENGTH = 10_000;
    private static final int MAX_KNOWLEDGE_LENGTH = 50_000;

    private final ChatClient chatClient;
    private final JdbcTemplate jdbcTemplate;
    private final ConversationService conversationService;

    public AgentController(ChatClient.Builder builder,
                           JdbcChatMemoryRepository chatMemoryRepository,
                           JdbcTemplate jdbcTemplate,
                           AgentTools agentTools,
                           ConversationService conversationService) {
        this.jdbcTemplate = jdbcTemplate;
        this.conversationService = conversationService;

        ChatMemory chatMemory = new LoggingChatMemory(
                MessageWindowChatMemory.builder()
                        .chatMemoryRepository(chatMemoryRepository)
                        .maxMessages(100)
                        .build());

        var hybridRetriever = new OracleHybridDocumentRetriever(
                jdbcTemplate, 5, "POLICY_HYBRID_IDX", "rrf");

        this.chatClient = builder
                .defaultSystem("""
                        You are ShopAssist, a customer support AI agent.

                        You have TOOLS for performing actions — always use them when the user asks to do something:
                        - listOrders: Lists ALL orders. No parameters needed. Call it directly when asked about orders.
                        - lookupOrderStatus: Checks status of a specific order by its ID (e.g. ORD-1001).
                        - initiateReturn: Starts a return for a delivered order. Needs order ID and reason.
                        - escalateToSupport: Creates a support ticket. Needs issue description, priority, and optional order ID.
                        - listSupportTickets: Lists all support tickets. No parameters needed.

                        You also have a KNOWLEDGE BASE with store policies (returns, shipping, support, etc.). \
                        When policy context is provided, use it to answer policy questions.

                        IMPORTANT RULES:
                        - When the user asks to perform an action, ALWAYS call the appropriate tool immediately. \
                        Do NOT ask for information the tool does not require.
                        - listOrders takes NO parameters — never ask for a customer ID or email, just call it.
                        - Only use knowledge context for policy or informational questions, not for actions.
                        - Be concise and direct. If you don't know something, say so.""")
                .defaultTools(agentTools)
                .defaultAdvisors(
                        MessageChatMemoryAdvisor.builder(chatMemory).build(),
                        RetrievalAugmentationAdvisor.builder()
                                .documentRetriever(hybridRetriever)
                                .queryAugmenter(ContextualQueryAugmenter.builder()
                                        .allowEmptyContext(true)
                                        .promptTemplate(new PromptTemplate("""
                                                The following store policy documents may be relevant:

                                                ---------------------
                                                {context}
                                                ---------------------

                                                Use these ONLY to answer questions about store policies \
                                                (returns, shipping, support, warranties, etc.).
                                                For action requests, use your tools. \
                                                For conversational questions, use the conversation history.

                                                {query}"""))
                                        .build())
                                .build()
                )
                .build();
    }

    @PostMapping("/chat")
    public ResponseEntity<String> chat(
            @RequestBody String message,
            @RequestHeader("X-Conversation-Id") String conversationId) {

        if (message == null || message.isBlank()) {
            return ResponseEntity.badRequest().body("Message cannot be empty.");
        }
        if (message.length() > MAX_MESSAGE_LENGTH) {
            return ResponseEntity.badRequest()
                    .body("Message exceeds maximum length of " + MAX_MESSAGE_LENGTH + " characters.");
        }

        log.info("[conv:{}] Incoming: \"{}\"", conversationId,
                message.length() > 200 ? message.substring(0, 200) + "..." : message);

        try {
            String response = chatClient.prompt()
                    .user(message)
                    .advisors(a -> a.param(ChatMemory.CONVERSATION_ID, conversationId))
                    .call()
                    .content();
            log.info("[conv:{}] Response: 200 OK ({} chars)", conversationId,
                    response != null ? response.length() : 0);
            conversationService.generateSummaryIfNeeded(conversationId, message);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("[conv:{}] Error processing chat request", conversationId, e);
            return ResponseEntity.internalServerError()
                    .body("Unable to process your request. Please try again later.");
        }
    }

    @GetMapping("/conversations")
    public ResponseEntity<List<ConversationInfo>> listConversations() {
        return ResponseEntity.ok(conversationService.listConversations());
    }

    @GetMapping("/conversations/{id}/messages")
    public ResponseEntity<List<MessageDto>> getMessages(@PathVariable("id") String conversationId) {
        List<MessageDto> messages = conversationService.getMessages(conversationId);
        if (messages.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(messages);
    }

    @PostMapping("/knowledge")
    public ResponseEntity<String> addKnowledge(@RequestBody String content) {
        if (content == null || content.isBlank()) {
            return ResponseEntity.badRequest().body("Content cannot be empty.");
        }
        if (content.length() > MAX_KNOWLEDGE_LENGTH) {
            return ResponseEntity.badRequest().body("Content exceeds maximum length of " + MAX_KNOWLEDGE_LENGTH + " characters.");
        }

        try {
            jdbcTemplate.update(
                    "INSERT INTO POLICY_DOCS (id, content) VALUES (sys_guid(), ?)",
                    content);
            return ResponseEntity.ok("Knowledge added.");
        } catch (Exception e) {
            log.error("Error adding knowledge to POLICY_DOCS", e);
            return ResponseEntity.internalServerError()
                    .body("Unable to store knowledge. Please try again later.");
        }
    }
}
