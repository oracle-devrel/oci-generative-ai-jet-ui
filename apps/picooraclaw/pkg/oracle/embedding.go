package oracle

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"

	"github.com/jasperan/picooraclaw/pkg/logger"
)

// EmbeddingService handles text-to-vector embedding.
// It supports two modes:
//   - "onnx": Uses Oracle's in-database VECTOR_EMBEDDING() with an ONNX model
//   - "api":  Calls an external OpenAI-compatible /v1/embeddings endpoint
type EmbeddingService struct {
	db        *sql.DB
	modelName string
	dims      int
	dimsOnce  sync.Once

	// API mode fields
	mode       string // "onnx" or "api"
	apiBase    string
	apiKey     string
	apiModel   string
	httpClient *http.Client
}

// NewEmbeddingService creates a new EmbeddingService using in-database ONNX mode.
func NewEmbeddingService(db *sql.DB, modelName string) (*EmbeddingService, error) {
	if err := validateSQLIdentifier(modelName); err != nil {
		return nil, fmt.Errorf("invalid ONNX model name: %w", err)
	}
	return &EmbeddingService{
		db:        db,
		modelName: modelName,
		dims:      384, // ALL_MINILM_L12_V2 outputs 384-dim vectors
		mode:      "onnx",
	}, nil
}

// NewAPIEmbeddingService creates an EmbeddingService that calls an external API.
// The API must be OpenAI-compatible (POST /v1/embeddings).
func NewAPIEmbeddingService(db *sql.DB, apiBase, apiKey, apiModel string) *EmbeddingService {
	return &EmbeddingService{
		db:       db,
		mode:     "api",
		apiBase:  apiBase,
		apiKey:   apiKey,
		apiModel: apiModel,
		dims:     0, // determined on first call
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// embeddingAPIRequest is the OpenAI-compatible request body.
type embeddingAPIRequest struct {
	Model string `json:"model"`
	Input string `json:"input"`
}

// embeddingAPIResponse is the OpenAI-compatible response body.
type embeddingAPIResponse struct {
	Data []struct {
		Embedding []float32 `json:"embedding"`
		Index     int       `json:"index"`
	} `json:"data"`
	Model string `json:"model"`
	Usage struct {
		PromptTokens int `json:"prompt_tokens"`
		TotalTokens  int `json:"total_tokens"`
	} `json:"usage"`
}

// EmbedText generates an embedding vector for the given text.
func (es *EmbeddingService) EmbedText(text string) ([]float32, error) {
	if text == "" {
		if es.dims > 0 {
			return make([]float32, es.dims), nil
		}
		return make([]float32, 384), nil
	}

	// Truncate to a safe max input length
	if len(text) > 512 {
		text = text[:512]
	}

	if es.mode == "api" {
		return es.embedViaAPI(text)
	}
	return es.embedViaONNX(text)
}

// embedViaONNX generates embeddings using Oracle's in-database VECTOR_EMBEDDING().
func (es *EmbeddingService) embedViaONNX(text string) ([]float32, error) {
	query := fmt.Sprintf(
		"SELECT VECTOR_EMBEDDING(%s USING :1 AS DATA) FROM DUAL",
		es.modelName,
	)

	var embedding []float32
	err := es.db.QueryRow(query, text).Scan(&embedding)
	if err != nil {
		return nil, fmt.Errorf("VECTOR_EMBEDDING failed: %w", err)
	}

	return embedding, nil
}

// embedViaAPI generates embeddings by calling an external OpenAI-compatible endpoint.
func (es *EmbeddingService) embedViaAPI(text string) ([]float32, error) {
	reqBody := embeddingAPIRequest{
		Model: es.apiModel,
		Input: text,
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal embedding request: %w", err)
	}

	url := es.apiBase + "/embeddings"
	req, err := http.NewRequest("POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create embedding request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+es.apiKey)

	resp, err := es.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("embedding API call failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read embedding response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("embedding API returned %d: %s", resp.StatusCode, string(respBody))
	}

	var apiResp embeddingAPIResponse
	if err := json.Unmarshal(respBody, &apiResp); err != nil {
		return nil, fmt.Errorf("failed to parse embedding response: %w", err)
	}

	if len(apiResp.Data) == 0 || len(apiResp.Data[0].Embedding) == 0 {
		return nil, fmt.Errorf("embedding API returned empty result")
	}

	embedding := apiResp.Data[0].Embedding

	// Set dims on first successful call (thread-safe)
	es.dimsOnce.Do(func() {
		es.dims = len(embedding)
		logger.InfoCF("oracle", "Embedding dimensions detected", map[string]interface{}{
			"dims":  es.dims,
			"model": es.apiModel,
		})
	})

	return embedding, nil
}

// EmbedTexts generates embeddings for multiple texts.
func (es *EmbeddingService) EmbedTexts(texts []string) ([][]float32, error) {
	results := make([][]float32, 0, len(texts))
	for _, text := range texts {
		emb, err := es.EmbedText(text)
		if err != nil {
			return nil, err
		}
		results = append(results, emb)
	}
	return results, nil
}

// CheckONNXLoaded checks if the ONNX model is loaded in the database.
// Always returns true for API mode (no ONNX needed).
func (es *EmbeddingService) CheckONNXLoaded() (bool, error) {
	if es.mode == "api" {
		return true, nil
	}
	var count int
	err := es.db.QueryRow(
		"SELECT COUNT(*) FROM USER_MINING_MODELS WHERE MODEL_NAME = :1",
		es.modelName,
	).Scan(&count)
	if err != nil {
		return false, fmt.Errorf("failed to check ONNX model: %w", err)
	}
	return count > 0, nil
}

// LoadONNXModel loads the ONNX model into the database using DBMS_VECTOR.
// No-op in API mode.
func (es *EmbeddingService) LoadONNXModel(onnxDir, onnxFile string) error {
	if es.mode == "api" {
		return nil
	}
	if err := validateSQLIdentifier(es.modelName); err != nil {
		return fmt.Errorf("invalid model name: %w", err)
	}
	if err := validateSQLIdentifier(onnxDir); err != nil {
		return fmt.Errorf("invalid ONNX directory name: %w", err)
	}
	// Sanitize onnxFile: allow alphanumeric, underscore, hyphen, and dot (for filenames like model.onnx)
	for _, r := range onnxFile {
		if r == '_' || r == '-' || r == '.' || (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			continue
		}
		return fmt.Errorf("invalid character %q in ONNX file name %q", r, onnxFile)
	}
	plsql := fmt.Sprintf(`BEGIN
		DBMS_VECTOR.LOAD_ONNX_MODEL(
			directory  => '%s',
			file_name  => '%s',
			model_name => '%s'
		);
	END;`, onnxDir, onnxFile, es.modelName)

	_, err := es.db.Exec(plsql)
	if err != nil {
		return fmt.Errorf("failed to load ONNX model: %w", err)
	}

	logger.InfoCF("oracle", "ONNX model loaded", map[string]interface{}{
		"model": es.modelName,
		"dir":   onnxDir,
		"file":  onnxFile,
	})
	return nil
}

// TestEmbedding tests if embedding generation works.
func (es *EmbeddingService) TestEmbedding() bool {
	_, err := es.EmbedText("test")
	return err == nil
}

// Dims returns the embedding dimensionality.
func (es *EmbeddingService) Dims() int {
	return es.dims
}

// ModelName returns the model name.
func (es *EmbeddingService) ModelName() string {
	if es.mode == "api" {
		return es.apiModel
	}
	return es.modelName
}

// Mode returns the embedding mode ("onnx" or "api").
func (es *EmbeddingService) Mode() string {
	return es.mode
}
