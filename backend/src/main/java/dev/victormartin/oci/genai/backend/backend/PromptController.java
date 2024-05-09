package dev.victormartin.oci.genai.backend.backend;

import com.oracle.bmc.model.BmcException;
import dev.victormartin.oci.genai.backend.backend.dao.Answer;
import dev.victormartin.oci.genai.backend.backend.dao.Prompt;
import dev.victormartin.oci.genai.backend.backend.data.Interaction;
import dev.victormartin.oci.genai.backend.backend.data.InteractionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.stereotype.Controller;
import org.springframework.web.util.HtmlUtils;

import java.util.Date;

@Controller
public class PromptController {
	Logger logger = LoggerFactory.getLogger(PromptController.class);

	@Value("${genai.model_id}")
	private String hardcodedModelId;

	@Autowired
	private final InteractionRepository interactionRepository;

	@Autowired
	OCIGenAIService genAI;

	public PromptController(InteractionRepository interactionRepository, OCIGenAIService genAI) {
		this.interactionRepository = interactionRepository;
		this.genAI = genAI;
	}

	@MessageMapping("/prompt")
	@SendToUser("/queue/answer")
	public Answer handlePrompt(Prompt prompt) {
		String promptEscaped = HtmlUtils.htmlEscape(prompt.content());
		logger.info("Prompt " + promptEscaped + " received, on model " + prompt.modelId() + " but using hardcoded one" +
				" " + hardcodedModelId);
		Interaction interaction = new Interaction();
		interaction.setConversationId(prompt.conversationId());
		interaction.setDatetimeRequest(new Date());
		interaction.setModelId(hardcodedModelId);
		interaction.setRequest(promptEscaped);
		Interaction saved = interactionRepository.save(interaction);
		try {
			if (prompt.content() == null || prompt.content().length()< 1) { throw  new InvalidPromptRequest(); }
//			if (prompt.modelId() == null || !prompt.modelId().startsWith("ocid1.generativeaimodel.")) { throw  new InvalidPromptRequest(); }
			String responseFromGenAI = genAI.request(promptEscaped, hardcodedModelId);
			saved.setDatetimeResponse(new Date());
			saved.setResponse(responseFromGenAI);
			interactionRepository.save(saved);
			return new Answer(responseFromGenAI, "");
		} catch (BmcException exception) {
			logger.error(exception.getOriginalMessage());
			String unmodifiedMessage = exception.getUnmodifiedMessage();
			int statusCode = exception.getStatusCode();
			String errorMessage = statusCode + " " + unmodifiedMessage;
			logger.error(errorMessage);
			saved.setErrorMessage(errorMessage);
			interactionRepository.save(saved);
			return new Answer("", errorMessage);
		} catch (InvalidPromptRequest exception) {
			int statusCode = HttpStatus.BAD_REQUEST.value();
			String errorMessage = statusCode + " Invalid Prompt ";
			logger.error(errorMessage);
			saved.setErrorMessage(errorMessage);
			interactionRepository.save(saved);
			return new Answer("", errorMessage);
		}
	}

}
