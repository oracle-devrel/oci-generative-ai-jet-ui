package com.example.news.genai.chat;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

import com.oracle.bmc.generativeaiinference.GenerativeAiInference;
import com.oracle.bmc.generativeaiinference.model.BaseChatRequest;
import com.oracle.bmc.generativeaiinference.model.BaseChatResponse;
import com.oracle.bmc.generativeaiinference.model.ChatChoice;
import com.oracle.bmc.generativeaiinference.model.ChatContent;
import com.oracle.bmc.generativeaiinference.model.ChatDetails;
import com.oracle.bmc.generativeaiinference.model.CohereChatRequest;
import com.oracle.bmc.generativeaiinference.model.CohereChatResponse;
import com.oracle.bmc.generativeaiinference.model.CohereMessage;
import com.oracle.bmc.generativeaiinference.model.GenericChatRequest;
import com.oracle.bmc.generativeaiinference.model.GenericChatResponse;
import com.oracle.bmc.generativeaiinference.model.Message;
import com.oracle.bmc.generativeaiinference.model.ServingMode;
import com.oracle.bmc.generativeaiinference.model.TextContent;
import com.oracle.bmc.generativeaiinference.model.UserMessage;
import com.oracle.bmc.generativeaiinference.requests.ChatRequest;
import com.oracle.bmc.generativeaiinference.responses.ChatResponse;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * OCI GenAI Chat
 */
@Component
public class OCIChatService implements ChatService {
    private final GenerativeAiInference client;
    private final ServingMode servingMode;
    private final String compartment;
    private final String preambleOverride;
    private final Double temperature;
    private final Double frequencyPenalty;
    private final Integer maxTokens;
    private final Double presencePenalty;
    private final Double topP;
    private final Integer topK;
    private final InferenceRequestType inferenceRequestType;
    private List<CohereMessage> cohereChatMessages;
    private List<ChatChoice> genericChatMessages;

    public OCIChatService(GenerativeAiInference aiClient,
                          @Qualifier("chatServingMode") ServingMode servingMode,
                          @Value("${oci.compartment}") String compartment,
                          @Value("${oci.chat.preambleOverride}") String preambleOverride,
                          @Value("${oci.chat.temperature}") Double temperature,
                          @Value("${oci.chat.frequencyPenalty}") Double frequencyPenalty,
                          @Value("${oci.chat.maxTokens}") Integer maxTokens,
                          @Value("${oci.chat.presencePenalty}") Double presencePenalty,
                          @Value("${oci.chat.topP}") Double topP,
                          @Value("${oci.chat.topK}") Integer topK,
                          @Value("${oci.chat.inferenceRequestType}") InferenceRequestType inferenceRequestType) {
        this.client = aiClient;
        this.servingMode = servingMode;
        this.compartment = compartment;
        this.preambleOverride = preambleOverride;

        this.temperature = Objects.requireNonNullElse(temperature, 1.0);
        this.frequencyPenalty = Objects.requireNonNullElse(
                frequencyPenalty,
                0.0
        );
        this.maxTokens = Objects.requireNonNullElse(maxTokens, 600);
        this.presencePenalty = Objects.requireNonNullElse(
                presencePenalty,
                0.0
        );
        this.topP = Objects.requireNonNullElse(topP, 0.75);
        this.inferenceRequestType = Objects.requireNonNullElse(
                inferenceRequestType,
                InferenceRequestType.COHERE
        );
        this.topK = Objects.requireNonNullElseGet(topK, () -> {
            if (this.inferenceRequestType == InferenceRequestType.COHERE) {
                return 0;
            }
            return -1;
        });
    }

    public enum InferenceRequestType {
        COHERE("COHERE"),
        LLAMA("LLAMA");

        private final String type;

        InferenceRequestType(String type) {
            this.type = type;
        }

        public String getType() {
            return type;
        }
    }

    /**
     * Chat using OCI GenAI.
     * @param prompt Prompt text sent to OCI GenAI chat model.
     * @return OCI GenAI ChatResponse
     */
    public String chat(String prompt) {
        ChatDetails chatDetails = ChatDetails.builder()
                .compartmentId(compartment)
                .servingMode(servingMode)
                .chatRequest(createChatRequest(prompt))
                .build();
        ChatRequest chatRequest = ChatRequest.builder()
                .body$(chatDetails)
                .build();
        ChatResponse response = client.chat(chatRequest);
        saveChatHistory(response);
        return extractText(response);
    }

    /**
     * Create a ChatRequest from a text prompt. Supports COHERE or LLAMA inference.
     * @param prompt To create a ChatRequest from.
     * @return A COHERE or LLAMA ChatRequest.
     */
    private BaseChatRequest createChatRequest(String prompt) {
        switch (inferenceRequestType) {
            case COHERE:
                return CohereChatRequest.builder()
                        .frequencyPenalty(frequencyPenalty)
                        .maxTokens(maxTokens)
                        .presencePenalty(presencePenalty)
                        .message(prompt)
                        .temperature(temperature)
                        .topP(topP)
                        .topK(topK)
                        .chatHistory(cohereChatMessages)
                        .preambleOverride(preambleOverride)
                        .build();
            case LLAMA:
                List<Message> messages = genericChatMessages == null ?
                        new ArrayList<>() :
                        genericChatMessages.stream()
                            .map(ChatChoice::getMessage)
                            .collect(Collectors.toList());
                ChatContent content = TextContent.builder()
                        .text(prompt)
                        .build();
                List<ChatContent> contents = new ArrayList<>();
                contents.add(content);
                UserMessage message = UserMessage.builder()
                        .name("USER")
                        .content(contents)
                        .build();
                messages.add(message);
                return GenericChatRequest.builder()
                        .messages(messages)
                        .frequencyPenalty(frequencyPenalty)
                        .temperature(temperature)
                        .maxTokens(maxTokens)
                        .presencePenalty(presencePenalty)
                        .topP(topP)
                        .topK(topK)
                        .build();
        }

        throw new IllegalArgumentException(String.format(
                "Unknown request type %s",
                inferenceRequestType
        ));
    }

    /**
     * Save the current chat history to memory.
     * @param chatResponse The latest chat response.
     */
    private void saveChatHistory(ChatResponse chatResponse) {
        BaseChatResponse bcr = chatResponse.getChatResult()
                .getChatResponse();
        if (bcr instanceof CohereChatResponse resp) {
            cohereChatMessages = resp.getChatHistory();
        } else if (bcr instanceof GenericChatResponse resp) {
            genericChatMessages = resp.getChoices();
        } else {
            throw new IllegalStateException(String.format(
                    "Unexpected chat response type: %s",
                    bcr.getClass().getName()
            ));
        }
    }

    /**
     * Extract text from an OCI GenAI ChatResponse.
     * @param chatResponse The response to extract text from.
     * @return The chat response text.
     */
    private String extractText(ChatResponse chatResponse) {
        BaseChatResponse bcr = chatResponse
                .getChatResult()
                .getChatResponse();
        if (bcr instanceof CohereChatResponse resp) {
            return resp.getText();
        } else if (bcr instanceof GenericChatResponse resp) {
            List<ChatChoice> choices =  resp.getChoices();
            List<ChatContent> contents = choices.get(choices.size() - 1)
                    .getMessage()
                    .getContent();
            ChatContent content = contents.get(contents.size() - 1);
            if (content instanceof TextContent) {
                return ((TextContent) content).getText();
            }
        }
        throw new IllegalStateException(String.format(
                "Unexpected chat response type: %s",
                bcr.getClass().getName()
        ));
    }
}