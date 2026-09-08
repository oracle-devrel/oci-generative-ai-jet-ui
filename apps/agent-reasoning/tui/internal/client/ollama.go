package client

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	OllamaHost = "http://localhost:11434"
)

// OllamaClient communicates with Ollama for model listing
type OllamaClient struct {
	baseURL string
	client  *http.Client
}

// OllamaModel represents a model from Ollama
type OllamaModel struct {
	Name       string `json:"name"`
	ModifiedAt string `json:"modified_at"`
	Size       int64  `json:"size"`
}

// OllamaTagsResponse is the response from /api/tags
type OllamaTagsResponse struct {
	Models []OllamaModel `json:"models"`
}

// NewOllamaClient creates a new Ollama client
func NewOllamaClient() *OllamaClient {
	return &OllamaClient{
		baseURL: OllamaHost,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// ListModels fetches available models from Ollama
func (c *OllamaClient) ListModels() ([]string, error) {
	resp, err := c.client.Get(c.baseURL + "/api/tags")
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Ollama: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Ollama returned status %d", resp.StatusCode)
	}

	var tagsResp OllamaTagsResponse
	if err := json.NewDecoder(resp.Body).Decode(&tagsResp); err != nil {
		return nil, fmt.Errorf("failed to parse Ollama response: %w", err)
	}

	models := make([]string, len(tagsResp.Models))
	for i, m := range tagsResp.Models {
		models[i] = m.Name
	}

	return models, nil
}

// IsAvailable checks if Ollama is running
func (c *OllamaClient) IsAvailable() bool {
	resp, err := c.client.Get(c.baseURL + "/api/tags")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
