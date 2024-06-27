package dev.victormartin.oci.genai.backend.backend.controller;

import com.oracle.bmc.generativeai.GenerativeAiClient;
import com.oracle.bmc.generativeai.model.ModelCapability;
import com.oracle.bmc.generativeai.requests.ListModelsRequest;
import com.oracle.bmc.generativeai.responses.ListModelsResponse;
import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;
import dev.victormartin.oci.genai.backend.backend.service.GenerativeAiClientService;
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
    private GenerativeAiClientService generativeAiClientService;

    @GetMapping("/api/genai/models")
    public List<GenAiModel> getModels() {
        logger.info("getModels()");
        ListModelsRequest listModelsRequest = ListModelsRequest.builder().compartmentId(COMPARTMENT_ID).build();
        GenerativeAiClient client = generativeAiClientService.getClient();
        ListModelsResponse response = client.listModels(listModelsRequest);
        return response.getModelCollection().getItems().stream().map(m -> {
            List<String> capabilities = m.getCapabilities().stream().map(ModelCapability::getValue).collect(Collectors.toList());
            GenAiModel model = new GenAiModel(m.getId(),m.getDisplayName(), m.getVendor(), m.getVersion(),
                    capabilities,
                    m.getTimeCreated());
            return model;
        }).collect(Collectors.toList());
    }
}
