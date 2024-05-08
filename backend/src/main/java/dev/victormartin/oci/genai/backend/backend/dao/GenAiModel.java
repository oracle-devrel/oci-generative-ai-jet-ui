package dev.victormartin.oci.genai.backend.backend.dao;

import java.util.Date;
import java.util.List;

public record GenAiModel(String id, String name, String vendor, String version, List<String> capabilities,
                         Date timeCreated) {
}
