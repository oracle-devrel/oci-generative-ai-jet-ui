package dev.victormartin.oci.genai.backend.backend.controller;

import com.oracle.bmc.generativeai.GenerativeAiClient;
import com.oracle.bmc.generativeai.model.ModelCapability;
import com.oracle.bmc.generativeai.requests.ListModelsRequest;
import com.oracle.bmc.generativeai.requests.ListEndpointsRequest;
import com.oracle.bmc.generativeai.responses.ListModelsResponse;
import com.oracle.bmc.generativeai.responses.ListEndpointsResponse;
import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;
import dev.victormartin.oci.genai.backend.backend.dao.GenAiEndpoint;
import dev.victormartin.oci.genai.backend.backend.service.GenAIModelsService;
import dev.victormartin.oci.genai.backend.backend.service.GenAiClientService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.stream.Collectors;

@RestController
public class GenAIController {
    Logger logger = LoggerFactory.getLogger(GenAIController.class);

    @Value("${genai.compartment_id}")
    private String COMPARTMENT_ID;

    @Autowired
    private GenAiClientService generativeAiClientService;

    @Autowired
    private GenAIModelsService genAIModelsService;

    @GetMapping("/api/genai/models")
    public List<GenAiModel> getModels() {
        logger.info("getModels()");
        List<GenAiModel> models = genAIModelsService.getModels();
        return models.stream()
                .filter(m -> m.capabilities().contains("CHAT"))
                .collect(Collectors.toList());
    }

    @GetMapping("/api/genai/endpoints")
    public List<GenAiEndpoint> getEndpoints() {
        logger.info("getEndpoints()");
        ListEndpointsRequest listEndpointsRequest = ListEndpointsRequest.builder().compartmentId(COMPARTMENT_ID)
                .build();
        GenerativeAiClient client = generativeAiClientService.getClient();
        ListEndpointsResponse response = client.listEndpoints(listEndpointsRequest);
        return response.getEndpointCollection().getItems().stream().map(e -> {
            GenAiEndpoint endpoint = new GenAiEndpoint(e.getId(), e.getDisplayName(), e.getLifecycleState(),
                    e.getModelId(), e.getTimeCreated());
            return endpoint;
        }).collect(Collectors.toList());
    }
}
