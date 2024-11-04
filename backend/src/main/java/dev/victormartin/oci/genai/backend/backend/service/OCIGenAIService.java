package dev.victormartin.oci.genai.backend.backend.service;

import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.ChatRequest;
import com.oracle.bmc.generativeaiinference.requests.GenerateTextRequest;
import com.oracle.bmc.generativeaiinference.requests.SummarizeTextRequest;
import com.oracle.bmc.generativeaiinference.responses.ChatResponse;
import com.oracle.bmc.generativeaiinference.responses.GenerateTextResponse;
import com.oracle.bmc.generativeaiinference.responses.SummarizeTextResponse;
import com.oracle.bmc.http.client.jersey.WrappedResponseInputStream;
import org.hibernate.boot.archive.scan.internal.StandardScanner;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class OCIGenAIService {
        @Value("${genai.compartment_id}")
        private String COMPARTMENT_ID;

        @Autowired
        private GenAiInferenceClientService generativeAiInferenceClientService;

        public String resolvePrompt(String input, String modelId, boolean finetune) {
                CohereChatRequest cohereChatRequest = CohereChatRequest.builder()
                        .message(input)
                        .maxTokens(600)
                        .temperature((double) 1)
                        .frequencyPenalty((double) 0)
                        .topP((double) 0.75)
                        .topK(0)
                        .isStream(false) // TODO websockets and streams
                        .build();

                ChatDetails chatDetails = ChatDetails.builder()
                        .servingMode(OnDemandServingMode.builder().modelId(modelId).build())
                        .compartmentId(COMPARTMENT_ID)
                        .chatRequest(cohereChatRequest)
                        .build();

                ChatRequest request = ChatRequest.builder()
                        .chatDetails(chatDetails)
                        .build();
                ChatResponse response = generativeAiInferenceClientService.getClient().chat(request);
                ChatResult chatResult = response.getChatResult();

                BaseChatResponse baseChatResponse = chatResult.getChatResponse();
                if (baseChatResponse instanceof CohereChatResponse) {
                        return ((CohereChatResponse)baseChatResponse).getText();
                } else if (baseChatResponse instanceof GenericChatResponse) {
                        List<ChatChoice> choices = ((GenericChatResponse) baseChatResponse).getChoices();
                        List<ChatContent> contents = choices.get(choices.size() - 1).getMessage().getContent();
                        ChatContent content = contents.get(contents.size() - 1);
                        if (content instanceof TextContent) {
                                return ((TextContent) content).getText();
                        }
                }
                throw new IllegalStateException("Unexpected chat response type: " + baseChatResponse.getClass().getName());
        }

        public String summaryText(String input, String modelId, boolean finetuned) {
                String response = resolvePrompt("Summarize this:\n" + input, modelId, finetuned);
                return response;
        }
}
