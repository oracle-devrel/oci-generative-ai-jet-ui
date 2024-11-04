package dev.victormartin.oci.genai.backend.backend.controller;

import com.oracle.bmc.model.BmcException;
import dev.victormartin.oci.genai.backend.backend.dao.Answer;
import dev.victormartin.oci.genai.backend.backend.dao.SummaryRequest;
import dev.victormartin.oci.genai.backend.backend.data.Interaction;
import dev.victormartin.oci.genai.backend.backend.data.InteractionRepository;
import dev.victormartin.oci.genai.backend.backend.data.InteractionType;
import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.HtmlUtils;

import java.util.Date;

@RestController
public class SummaryController {
    Logger logger = LoggerFactory.getLogger(SummaryController.class);

    @Value("${genai.summarization_model_id}")
    String summarizationModelId;

    @Autowired
    OCIGenAIService ociGenAIService;

    @Autowired
    private InteractionRepository interactionRepository;

    @PostMapping("/api/genai/summary")
    public Answer postSummaryText(@RequestBody SummaryRequest summaryRequest,
                                  @RequestHeader("conversationID") String conversationId,
                                  @RequestHeader("modelId") String modelId) {
        logger.info("postSummaryText()");
        String contentEscaped = HtmlUtils.htmlEscape(summaryRequest.content());
        logger.info("contentEscaped: {}...", contentEscaped.substring(0, 50));
        Interaction interaction = new Interaction();
        interaction.setType(InteractionType.SUMMARY_TEXT);
        interaction.setConversationId(conversationId);
        interaction.setDatetimeRequest(new Date());
        interaction.setModelId(summarizationModelId);
        interaction.setRequest(contentEscaped);
        Interaction saved = interactionRepository.save(interaction);
        try {
            String summaryText = ociGenAIService.summaryText(contentEscaped, summarizationModelId, false);
            saved.setDatetimeResponse(new Date());
            saved.setResponse(summaryText);
            interactionRepository.save(saved);
            logger.info("summaryText: {}...", summaryText.substring(0, 50));
            Answer answer = new Answer();
            answer.setContent(summaryText);
            answer.setErrorMessage("");
            return answer;
        } catch (BmcException e) {
            String unmodifiedMessage = e.getUnmodifiedMessage();
            int statusCode = e.getStatusCode();
            String errorMessage = statusCode + " " + unmodifiedMessage;
            logger.error(errorMessage);
            saved.setErrorMessage(errorMessage);
            interactionRepository.save(saved);
            Answer answer = new Answer("", errorMessage);
            return answer;
        } catch (Exception e) {
            String errorMessage = e.getLocalizedMessage();
            logger.error(errorMessage);
            saved.setErrorMessage(errorMessage);
            interactionRepository.save(saved);
            Answer answer = new Answer("", errorMessage);
            return answer;
        }
    }
}
