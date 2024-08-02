package dev.victormartin.oci.genai.backend.backend.data;

import jakarta.persistence.*;

import java.util.Date;
import java.util.Objects;

@Entity
public class Interaction {
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    Long id;

    String conversationId;

    @Enumerated(EnumType.STRING)
    InteractionType type;

    @Temporal(TemporalType.DATE)
    Date datetimeRequest;

    String modelId;

    @Lob
    @Column
    String request;

    @Temporal(TemporalType.DATE)
    Date datetimeResponse;

    @Lob
    @Column
    String response;

    @Lob
    @Column
    String errorMessage;

    public Interaction() {
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Interaction that = (Interaction) o;
        return Objects.equals(id, that.id) && Objects.equals(conversationId, that.conversationId) && type == that.type && Objects.equals(datetimeRequest, that.datetimeRequest) && Objects.equals(modelId, that.modelId) && Objects.equals(request, that.request) && Objects.equals(datetimeResponse, that.datetimeResponse) && Objects.equals(response, that.response) && Objects.equals(errorMessage, that.errorMessage);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, conversationId, type, datetimeRequest, modelId, request, datetimeResponse, response, errorMessage);
    }

    public Long getId() {
        return id;
    }

    public String getConversationId() {
        return conversationId;
    }

    public void setConversationId(String conversationId) {
        this.conversationId = conversationId;
    }

    public InteractionType getType() {
        return type;
    }

    public void setType(InteractionType type) {
        this.type = type;
    }

    public Date getDatetimeRequest() {
        return datetimeRequest;
    }

    public void setDatetimeRequest(Date datetimeRequest) {
        this.datetimeRequest = datetimeRequest;
    }

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getRequest() {
        return request;
    }

    public void setRequest(String request) {
        this.request = request;
    }

    public Date getDatetimeResponse() {
        return datetimeResponse;
    }

    public void setDatetimeResponse(Date datetimeResponse) {
        this.datetimeResponse = datetimeResponse;
    }

    public String getResponse() {
        return response;
    }

    public void setResponse(String response) {
        this.response = response;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
}
