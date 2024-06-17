package dev.victormartin.oci.genai.backend.backend.controller;

import com.oracle.bmc.model.BmcException;
import dev.victormartin.oci.genai.backend.backend.InvalidPromptRequest;
import dev.victormartin.oci.genai.backend.backend.dao.Answer;
import dev.victormartin.oci.genai.backend.backend.dao.Prompt;
import dev.victormartin.oci.genai.backend.backend.data.Interaction;
import dev.victormartin.oci.genai.backend.backend.data.InteractionRepository;
import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.messaging.simp.annotation.SubscribeMapping;
import org.springframework.stereotype.Controller;
import org.springframework.web.util.HtmlUtils;

import java.util.Date;

@Controller
public class SummaryController {
	Logger logger = LoggerFactory.getLogger(SummaryController.class);

	@SendToUser("/queue/summary")
	public Answer handleSummary(String summary) {
		logger.info("handleSummary");
		return new Answer(summary , "");
	}

}
