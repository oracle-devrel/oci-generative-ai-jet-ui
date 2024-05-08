package dev.victormartin.oci.genai.backend.backend;

import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.GenerateTextRequest;
import com.oracle.bmc.generativeaiinference.responses.GenerateTextResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.stream.Collectors;

@Service
public class OCIGenAIService {
    @Value("${genai.compartment_id}")
    private String COMPARTMENT_ID;

    @Autowired
    private GenerativeAiInferenceClient generativeAiInferenceClient;

    public String request(String input, String modelId) {
        // Build generate text request, send, and get response
        CohereLlmInferenceRequest llmInferenceRequest =
                CohereLlmInferenceRequest.builder()
                        .prompt(input)
                        .maxTokens(600)
                        .temperature((double)1)
                        .frequencyPenalty((double)0)
                        .topP((double)0.75)
                        .isStream(false)
                        .isEcho(false)
                        .build();

        GenerateTextDetails generateTextDetails = GenerateTextDetails.builder()
                .servingMode(OnDemandServingMode.builder().modelId(modelId).build())
                .compartmentId(COMPARTMENT_ID)
                .inferenceRequest(llmInferenceRequest)
                .build();
        GenerateTextRequest generateTextRequest = GenerateTextRequest.builder()
                .generateTextDetails(generateTextDetails)
                .build();
        GenerateTextResponse generateTextResponse = generativeAiInferenceClient.generateText(generateTextRequest);
        CohereLlmInferenceResponse response =
                (CohereLlmInferenceResponse) generateTextResponse.getGenerateTextResult().getInferenceResponse();
        String responseTexts = response.getGeneratedTexts().stream().map(t -> t.getText()).collect(Collectors.joining(","));
        return responseTexts;
    }
}
