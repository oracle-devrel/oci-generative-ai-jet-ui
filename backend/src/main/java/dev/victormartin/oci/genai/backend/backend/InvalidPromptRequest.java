package dev.victormartin.oci.genai.backend.backend;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(code = HttpStatus.BAD_REQUEST, reason = "Invalid request params")
public class InvalidPromptRequest extends RuntimeException {


}
