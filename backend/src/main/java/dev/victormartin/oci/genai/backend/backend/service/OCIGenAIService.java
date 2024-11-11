package dev.victormartin.oci.genai.backend.backend.service;

import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.model.Message;
import com.oracle.bmc.generativeaiinference.requests.ChatRequest;
import com.oracle.bmc.generativeaiinference.responses.ChatResponse;
import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class OCIGenAIService {

        Logger log = LoggerFactory.getLogger(OCIGenAIService.class);

        @Value("${genai.compartment_id}")
        private String COMPARTMENT_ID;

        @Autowired
        private GenAiInferenceClientService generativeAiInferenceClientService;

        @Autowired
        private GenAIModelsService genAIModelsService;

        public String resolvePrompt(String input, String modelId, boolean finetune, boolean summarization) {

                List<GenAiModel> models = genAIModelsService.getModels();
                GenAiModel currentModel = models.stream()
                        .filter(m-> modelId.equals(m.id()))
                        .findFirst()
                        .orElseThrow();

                log.info("Model {} with finetune {}", currentModel.name(), finetune? "yes" : "no");

                double temperature = summarization?0.0:0.5;

                String inputText = summarization?"Summarize this text:\n" + input: input;

                        ChatDetails chatDetails;
                switch (currentModel.vendor()) {
                        case "cohere":
                                CohereChatRequest cohereChatRequest = CohereChatRequest.builder()
                                        .message(inputText)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double) 0)
                                        .topP(0.75)
                                        .topK(0)
                                        .isStream(false) // TODO websockets and streams
                                        .build();

                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(cohereChatRequest)
                                        .build();
                                break;
                        case "meta":
                                ChatContent content = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> contents = new ArrayList<>();
                                contents.add(content);
                                List<Message> messages = new ArrayList<>();
                                Message message = new UserMessage(contents, "user");
                                messages.add(message);
                                GenericChatRequest genericChatRequest = GenericChatRequest.builder()
                                        .messages(messages)
                                        .maxTokens(600)
                                        .temperature((double)1)
                                        .frequencyPenalty((double)0)
                                        .presencePenalty((double)0)
                                        .topP(0.75)
                                        .topK(-1)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(genericChatRequest)
                                        .build();
                                break;
                        default:
                                throw new IllegalStateException("Unexpected value: " + currentModel.vendor());
                }

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
                String response = resolvePrompt(input, modelId, finetuned, true);
                return response;
        }
}
