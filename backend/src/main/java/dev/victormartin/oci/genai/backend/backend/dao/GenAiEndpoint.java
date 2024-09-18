package dev.victormartin.oci.genai.backend.backend.dao;

import java.util.Date;
import com.oracle.bmc.generativeai.model.Endpoint;

public record GenAiEndpoint(String id, String name, Endpoint.LifecycleState state, String model, Date timeCreated) {
}
