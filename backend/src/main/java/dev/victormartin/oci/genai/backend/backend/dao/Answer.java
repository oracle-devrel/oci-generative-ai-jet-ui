package dev.victormartin.oci.genai.backend.backend.dao;

public class Answer {

	private String content;

	private String errorMessage;

	public Answer() {
	}

	public Answer(String content, String errorMessage) {
		this.content = content;
		this.errorMessage = errorMessage;
	}
	public void setContent(String content) {
		this.content = content;
	}

	public String getContent() {
		return content;
	}

	public String getErrorMessage() {
		return errorMessage;
	}

	public void setErrorMessage(String errorMessage) {
		this.errorMessage = errorMessage;
	}

}
