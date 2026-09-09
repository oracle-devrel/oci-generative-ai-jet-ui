package com.example.news.genai.embedding;

import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import com.example.news.genai.vectorstore.VectorDataAdapter;
import com.oracle.bmc.generativeaiinference.GenerativeAiInference;
import com.oracle.bmc.generativeaiinference.model.EmbedTextDetails;
import com.oracle.bmc.generativeaiinference.model.ServingMode;
import com.oracle.bmc.generativeaiinference.requests.EmbedTextRequest;
import com.oracle.bmc.generativeaiinference.responses.EmbedTextResponse;
import oracle.sql.VECTOR;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * OCI GenAI implementation of Langchain4j EmbeddingModel
 */
@Component
public class OCIEmbeddingService implements EmbeddingService {
    /**
     * OCI GenAI accepts a maximum of 96 inputs per embedding request. If the Langchain input is greater
     * than 96 segments, the input will be split into chunks of this size.
     */
    private static final int EMBEDDING_BATCH_SIZE = 96;

    private final ServingMode servingMode;
    protected final String compartmentId;
    private final GenerativeAiInference aiClient;
    private final VectorDataAdapter vectorDataAdapter;
    /**
     * OCI GenAi accepts a maximum of 512 tokens per embedding. If the number of tokens exceeds this amount,
     * and the embedding truncation value is set to None (default), an error will be received.
     * <p>
     * If truncate is set to START, embeddings will be truncated to 512 tokens from the start of the input.
     * If truncate is set to END, embeddings will be truncated to 512 tokens from the end of the input.
     */
    private final EmbedTextDetails.Truncate truncate;

    public OCIEmbeddingService(@Qualifier("embedServingMode") ServingMode servingMode,
                               @Value("${oci.compartment}") String compartmentId,
                               GenerativeAiInference aiClient,
                               VectorDataAdapter vectorDataAdapter,
                               EmbedTextDetails.Truncate truncate) {
        this.servingMode = servingMode;
        this.compartmentId = compartmentId;
        this.aiClient = aiClient;
        this.vectorDataAdapter = vectorDataAdapter;
        this.truncate = truncate == null ? EmbedTextDetails.Truncate.None : truncate;
    }

    /**
     * Embeds the text content of a list of TextSegments.
     *
     * @param chunks the text chunks to embed.
     * @return the embeddings.
     */
    public List<VECTOR> embedAll(List<String> chunks) {
        List<VECTOR> embeddings = new ArrayList<>();
        List<List<String>> batches = toBatches(chunks);
        for (List<String> batch : batches) {
            EmbedTextRequest embedTextRequest = toEmbedTextRequest(batch);
            EmbedTextResponse response = aiClient.embedText(embedTextRequest);
            embeddings.addAll(toEmbeddings(response, batch));
        }
        return embeddings;
    }

    private List<List<String>> toBatches(List<String> textSegments) {
        int size = textSegments.size();
        List<List<String>> batches = new ArrayList<>();
        for (int i = 0; i < textSegments.size(); i+=EMBEDDING_BATCH_SIZE) {
            batches.add(textSegments.subList(i, Math.min(i + EMBEDDING_BATCH_SIZE, size)));
        }
        return batches;
    }

    private EmbedTextRequest toEmbedTextRequest(List<String> batch) {
        EmbedTextDetails embedTextDetails = EmbedTextDetails.builder()
                .servingMode(servingMode)
                .compartmentId(compartmentId)
                .inputs(batch)
                .truncate(truncate)
                .build();
        return EmbedTextRequest.builder().embedTextDetails(embedTextDetails).build();
    }

    private List<VECTOR> toEmbeddings(EmbedTextResponse response, List<String> batch) {
        List<List<Float>> embeddings = response.getEmbedTextResult().getEmbeddings();
        return embeddings.stream().map(embedding -> {
                    try {
                        return vectorDataAdapter.toVECTOR(embedding);
                    } catch (SQLException ex) {
                        throw new RuntimeException(ex);
                    }
                })
                .collect(Collectors.toList());
    }
}
