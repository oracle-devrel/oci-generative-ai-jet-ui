package client

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	ServerHost = "http://localhost:8080"
)

// ServerClient communicates with server.py
type ServerClient struct {
	baseURL string
	client  *http.Client
}

// GenerateRequest is the request body for /api/generate
type GenerateRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

// GenerateResponse is a single response chunk from /api/generate
type GenerateResponse struct {
	Model     string `json:"model"`
	CreatedAt string `json:"created_at"`
	Response  string `json:"response"`
	Done      bool   `json:"done"`
}

// NewServerClient creates a new server client
func NewServerClient() *ServerClient {
	return &ServerClient{
		baseURL: ServerHost,
		client: &http.Client{
			Timeout: 0, // No timeout for streaming
		},
	}
}

// Generate sends a query to the server and returns a channel of response chunks
func (c *ServerClient) Generate(ctx context.Context, model, prompt string) (<-chan GenerateResponse, <-chan error) {
	respChan := make(chan GenerateResponse, 100)
	errChan := make(chan error, 1)

	go func() {
		defer close(respChan)
		defer close(errChan)

		reqBody := GenerateRequest{
			Model:  model,
			Prompt: prompt,
			Stream: true,
		}

		body, err := json.Marshal(reqBody)
		if err != nil {
			errChan <- fmt.Errorf("failed to marshal request: %w", err)
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate", bytes.NewReader(body))
		if err != nil {
			errChan <- fmt.Errorf("failed to create request: %w", err)
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errChan <- fmt.Errorf("failed to send request: %w", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			errChan <- fmt.Errorf("server returned status %d", resp.StatusCode)
			return
		}

		scanner := bufio.NewScanner(resp.Body)
		// Increase buffer size for large responses
		scanner.Buffer(make([]byte, 64*1024), 1024*1024)

		for scanner.Scan() {
			select {
			case <-ctx.Done():
				return
			default:
			}

			line := scanner.Text()
			if line == "" {
				continue
			}

			var genResp GenerateResponse
			if err := json.Unmarshal([]byte(line), &genResp); err != nil {
				// Skip malformed lines
				continue
			}

			respChan <- genResp

			if genResp.Done {
				return
			}
		}

		if err := scanner.Err(); err != nil {
			errChan <- fmt.Errorf("error reading response: %w", err)
		}
	}()

	return respChan, errChan
}

// GenerateSync sends a query and waits for the complete response
func (c *ServerClient) GenerateSync(ctx context.Context, model, prompt string) (string, error) {
	respChan, errChan := c.Generate(ctx, model, prompt)

	var fullResponse string
	for {
		select {
		case resp, ok := <-respChan:
			if !ok {
				return fullResponse, nil
			}
			fullResponse += resp.Response
			if resp.Done {
				return fullResponse, nil
			}
		case err := <-errChan:
			if err != nil {
				return fullResponse, err
			}
		case <-ctx.Done():
			return fullResponse, ctx.Err()
		}
	}
}

// ParameterSchema describes one tunable hyperparameter.
type ParameterSchema struct {
	Type        string  `json:"type"`
	Default     float64 `json:"default"`
	Min         float64 `json:"min"`
	Max         float64 `json:"max"`
	Description string  `json:"description"`
}

// AgentMeta holds metadata for one agent from /api/agents.
type AgentMeta struct {
	ID            string                     `json:"id"`
	Name          string                     `json:"name"`
	Description   string                     `json:"description"`
	Reference     string                     `json:"reference"`
	BestFor       string                     `json:"best_for"`
	Tradeoffs     string                     `json:"tradeoffs"`
	HasVisualizer bool                       `json:"has_visualizer"`
	Parameters    map[string]ParameterSchema `json:"parameters"`
}

// AgentsResponse is the response from GET /api/agents.
type AgentsResponse struct {
	Agents []AgentMeta `json:"agents"`
	Count  int         `json:"count"`
}

// StructuredEvent is one event from /api/generate_structured.
type StructuredEvent struct {
	EventType string                 `json:"event_type"`
	Data      map[string]interface{} `json:"data"`
	IsUpdate  bool                   `json:"is_update"`
}

// ListAgents calls GET /api/agents and returns agent metadata.
func (c *ServerClient) ListAgents() ([]AgentMeta, error) {
	resp, err := c.client.Get(c.baseURL + "/api/agents")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result AgentsResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Agents, nil
}

// GenerateStructured calls POST /api/generate_structured and streams StructuredEvent objects.
func (c *ServerClient) GenerateStructured(ctx context.Context, model, prompt string, params map[string]float64) (<-chan StructuredEvent, <-chan error) {
	eventCh := make(chan StructuredEvent, 100)
	errCh := make(chan error, 1)

	go func() {
		defer close(eventCh)
		defer close(errCh)

		body := map[string]interface{}{
			"model":  model,
			"prompt": prompt,
			"stream": true,
		}
		if len(params) > 0 {
			body["parameters"] = params
		}

		jsonBody, err := json.Marshal(body)
		if err != nil {
			errCh <- err
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate_structured", bytes.NewReader(jsonBody))
		if err != nil {
			errCh <- err
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errCh <- err
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			errCh <- fmt.Errorf("server returned status %d for generate_structured", resp.StatusCode)
			return
		}

		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var event StructuredEvent
			if err := json.Unmarshal([]byte(line), &event); err != nil {
				continue // skip malformed lines
			}
			select {
			case eventCh <- event:
			case <-ctx.Done():
				return
			}
		}
	}()

	return eventCh, errCh
}

// GenerateWithParams is like Generate but includes hyperparameters.
func (c *ServerClient) GenerateWithParams(ctx context.Context, model, prompt string, params map[string]float64) (<-chan GenerateResponse, <-chan error) {
	respCh := make(chan GenerateResponse, 100)
	errCh := make(chan error, 1)

	go func() {
		defer close(respCh)
		defer close(errCh)

		body := map[string]interface{}{
			"model":  model,
			"prompt": prompt,
			"stream": true,
		}
		if len(params) > 0 {
			body["parameters"] = params
		}

		jsonBody, err := json.Marshal(body)
		if err != nil {
			errCh <- err
			return
		}

		req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/api/generate", bytes.NewReader(jsonBody))
		if err != nil {
			errCh <- err
			return
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.client.Do(req)
		if err != nil {
			errCh <- err
			return
		}
		defer resp.Body.Close()

		scanner := bufio.NewScanner(resp.Body)
		scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}
			var genResp GenerateResponse
			if err := json.Unmarshal([]byte(line), &genResp); err != nil {
				continue
			}
			select {
			case respCh <- genResp:
			case <-ctx.Done():
				return
			}
		}
	}()

	return respCh, errCh
}

// DebugStepResponse is the response from POST /api/debug/step.
type DebugStepResponse struct {
	Event map[string]interface{} `json:"event"`
	Done  bool                   `json:"done"`
}

// DebugRunResponse is the response from POST /api/debug/run.
type DebugRunResponse struct {
	Events []map[string]interface{} `json:"events"`
}

// DebugStart starts a new debug session and returns the session ID.
func (c *ServerClient) DebugStart(model, prompt string, params map[string]float64) (string, error) {
	body := map[string]interface{}{
		"model":  model,
		"prompt": prompt,
	}
	if len(params) > 0 {
		body["parameters"] = params
	}

	jsonBody, _ := json.Marshal(body)
	resp, err := c.client.Post(c.baseURL+"/api/debug/start", "application/json", bytes.NewReader(jsonBody))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		SessionID string `json:"session_id"`
		Error     string `json:"error"`
	}
	json.NewDecoder(resp.Body).Decode(&result)
	if result.Error != "" {
		return "", fmt.Errorf("debug start error: %s", result.Error)
	}
	return result.SessionID, nil
}

// DebugStep fetches the next event from a debug session.
// Returns (event, done, error). When done is true, the session is complete.
func (c *ServerClient) DebugStep(sessionID string) (*StructuredEvent, bool, error) {
	body, _ := json.Marshal(map[string]string{"session_id": sessionID})
	resp, err := c.client.Post(c.baseURL+"/api/debug/step", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, false, err
	}
	defer resp.Body.Close()

	var result DebugStepResponse
	json.NewDecoder(resp.Body).Decode(&result)

	if result.Done || result.Event == nil {
		return nil, true, nil
	}

	eventType, _ := result.Event["event_type"].(string)
	data, _ := result.Event["data"].(map[string]interface{})
	if data == nil {
		data = map[string]interface{}{}
	}
	event := &StructuredEvent{
		EventType: eventType,
		Data:      data,
	}
	if v, ok := result.Event["is_update"].(bool); ok {
		event.IsUpdate = v
	}
	return event, false, nil
}

// DebugRun disables step-by-step pausing and drains all remaining events.
func (c *ServerClient) DebugRun(sessionID string) ([]StructuredEvent, error) {
	body, _ := json.Marshal(map[string]string{"session_id": sessionID})
	resp, err := c.client.Post(c.baseURL+"/api/debug/run", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result DebugRunResponse
	json.NewDecoder(resp.Body).Decode(&result)

	var events []StructuredEvent
	for _, raw := range result.Events {
		eventType, _ := raw["event_type"].(string)
		data, _ := raw["data"].(map[string]interface{})
		if data == nil {
			data = map[string]interface{}{}
		}
		events = append(events, StructuredEvent{
			EventType: eventType,
			Data:      data,
		})
	}
	return events, nil
}

// DebugCancel cancels and removes a debug session.
func (c *ServerClient) DebugCancel(sessionID string) error {
	req, err := http.NewRequest("DELETE", c.baseURL+"/api/debug/"+sessionID, nil)
	if err != nil {
		return err
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}

// IsHealthy checks if the server is responding
func (c *ServerClient) IsHealthy() bool {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/api/tags", nil)
	if err != nil {
		return false
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
