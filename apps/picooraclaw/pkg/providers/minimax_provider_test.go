package providers

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/jasperan/picooraclaw/pkg/config"
)

func TestMiniMaxProvider_ChatRoundTrip(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat/completions" {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		if r.Header.Get("Authorization") != "Bearer test-minimax-key" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		var reqBody map[string]interface{}
		json.NewDecoder(r.Body).Decode(&reqBody)

		// Verify model is passed correctly
		if reqBody["model"] != "MiniMax-M2.7" {
			http.Error(w, "unexpected model", http.StatusBadRequest)
			return
		}

		resp := map[string]interface{}{
			"id":      "chatcmpl-test",
			"object":  "chat.completion",
			"model":   reqBody["model"],
			"choices": []map[string]interface{}{
				{
					"index": 0,
					"message": map[string]interface{}{
						"role":    "assistant",
						"content": "Hello from MiniMax!",
					},
					"finish_reason": "stop",
				},
			},
			"usage": map[string]interface{}{
				"prompt_tokens":     10,
				"completion_tokens": 5,
				"total_tokens":      15,
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	provider := NewHTTPProvider("test-minimax-key", server.URL, "")

	messages := []Message{{Role: "user", Content: "Hello"}}
	resp, err := provider.Chat(context.Background(), messages, nil, "MiniMax-M2.7", map[string]interface{}{
		"max_tokens": 1024,
	})
	if err != nil {
		t.Fatalf("Chat() error: %v", err)
	}
	if resp.Content != "Hello from MiniMax!" {
		t.Errorf("Content = %q, want %q", resp.Content, "Hello from MiniMax!")
	}
	if resp.FinishReason != "stop" {
		t.Errorf("FinishReason = %q, want %q", resp.FinishReason, "stop")
	}
	if resp.Usage.PromptTokens != 10 {
		t.Errorf("PromptTokens = %d, want 10", resp.Usage.PromptTokens)
	}
	if resp.Usage.CompletionTokens != 5 {
		t.Errorf("CompletionTokens = %d, want 5", resp.Usage.CompletionTokens)
	}
}

func TestMiniMaxProvider_TemperatureClamp(t *testing.T) {
	tests := []struct {
		name        string
		temperature float64
		wantTemp    float64
	}{
		{"zero clamped to 1.0", 0.0, 1.0},
		{"negative clamped to 1.0", -0.5, 1.0},
		{"above 1.0 clamped to 1.0", 1.5, 1.0},
		{"valid temperature passed through", 0.7, 0.7},
		{"max valid temperature", 1.0, 1.0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var capturedTemp float64
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				var reqBody map[string]interface{}
				json.NewDecoder(r.Body).Decode(&reqBody)
				if temp, ok := reqBody["temperature"].(float64); ok {
					capturedTemp = temp
				}
				resp := map[string]interface{}{
					"choices": []map[string]interface{}{
						{"message": map[string]interface{}{"content": "ok"}, "finish_reason": "stop"},
					},
				}
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(resp)
			}))
			defer server.Close()

			provider := NewHTTPProvider("test-key", server.URL, "")
			messages := []Message{{Role: "user", Content: "test"}}
			_, err := provider.Chat(context.Background(), messages, nil, "MiniMax-M2.7", map[string]interface{}{
				"temperature": tt.temperature,
			})
			if err != nil {
				t.Fatalf("Chat() error: %v", err)
			}
			if capturedTemp != tt.wantTemp {
				t.Errorf("temperature = %f, want %f", capturedTemp, tt.wantTemp)
			}
		})
	}
}

func TestMiniMaxProvider_ModelPrefixStripping(t *testing.T) {
	var capturedModel string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var reqBody map[string]interface{}
		json.NewDecoder(r.Body).Decode(&reqBody)
		capturedModel = reqBody["model"].(string)
		resp := map[string]interface{}{
			"choices": []map[string]interface{}{
				{"message": map[string]interface{}{"content": "ok"}, "finish_reason": "stop"},
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	provider := NewHTTPProvider("test-key", server.URL, "")
	messages := []Message{{Role: "user", Content: "test"}}

	_, err := provider.Chat(context.Background(), messages, nil, "minimax/MiniMax-M2.7", map[string]interface{}{})
	if err != nil {
		t.Fatalf("Chat() error: %v", err)
	}
	if capturedModel != "MiniMax-M2.7" {
		t.Errorf("model = %q, want %q (prefix should be stripped)", capturedModel, "MiniMax-M2.7")
	}
}

func TestMiniMaxProvider_ToolCalling(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var reqBody map[string]interface{}
		json.NewDecoder(r.Body).Decode(&reqBody)

		// Verify tools are included in the request
		if _, ok := reqBody["tools"]; !ok {
			http.Error(w, "tools not found in request", http.StatusBadRequest)
			return
		}

		resp := map[string]interface{}{
			"choices": []map[string]interface{}{
				{
					"message": map[string]interface{}{
						"content": "",
						"tool_calls": []map[string]interface{}{
							{
								"id":   "call_123",
								"type": "function",
								"function": map[string]interface{}{
									"name":      "get_weather",
									"arguments": `{"city":"Tokyo"}`,
								},
							},
						},
					},
					"finish_reason": "tool_calls",
				},
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	provider := NewHTTPProvider("test-key", server.URL, "")
	messages := []Message{{Role: "user", Content: "What's the weather in Tokyo?"}}
	tools := []ToolDefinition{
		{
			Type: "function",
			Function: ToolFunctionDefinition{
				Name:        "get_weather",
				Description: "Get weather for a city",
				Parameters: map[string]interface{}{
					"type":       "object",
					"properties": map[string]interface{}{"city": map[string]interface{}{"type": "string"}},
					"required":   []interface{}{"city"},
				},
			},
		},
	}

	resp, err := provider.Chat(context.Background(), messages, tools, "MiniMax-M2.7", map[string]interface{}{})
	if err != nil {
		t.Fatalf("Chat() error: %v", err)
	}
	if len(resp.ToolCalls) != 1 {
		t.Fatalf("len(ToolCalls) = %d, want 1", len(resp.ToolCalls))
	}
	if resp.ToolCalls[0].Name != "get_weather" {
		t.Errorf("ToolCalls[0].Name = %q, want %q", resp.ToolCalls[0].Name, "get_weather")
	}
	if resp.ToolCalls[0].Arguments["city"] != "Tokyo" {
		t.Errorf("ToolCalls[0].Arguments[city] = %q, want %q", resp.ToolCalls[0].Arguments["city"], "Tokyo")
	}
}

func TestMiniMaxProvider_DefaultBaseURL(t *testing.T) {
	provider := NewHTTPProvider("test-key", "https://api.minimax.io/v1", "")
	if provider.apiBase != "https://api.minimax.io/v1" {
		t.Errorf("apiBase = %q, want %q", provider.apiBase, "https://api.minimax.io/v1")
	}
}

func TestMiniMaxProvider_Streaming(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var reqBody map[string]interface{}
		json.NewDecoder(r.Body).Decode(&reqBody)

		if reqBody["stream"] != true {
			http.Error(w, "stream not enabled", http.StatusBadRequest)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		flusher := w.(http.Flusher)

		chunks := []string{
			`data: {"choices":[{"delta":{"content":"Hello"},"index":0}]}`,
			`data: {"choices":[{"delta":{"content":" from"},"index":0}]}`,
			`data: {"choices":[{"delta":{"content":" MiniMax!"},"index":0,"finish_reason":"stop"}]}`,
			`data: [DONE]`,
		}
		for _, chunk := range chunks {
			w.Write([]byte(chunk + "\n\n"))
			flusher.Flush()
		}
	}))
	defer server.Close()

	provider := NewHTTPProvider("test-key", server.URL, "")
	messages := []Message{{Role: "user", Content: "test"}}

	var accumulated string
	callback := StreamCallback(func(chunk StreamChunk) {
		accumulated += chunk.Content
	})

	resp, err := provider.Chat(context.Background(), messages, nil, "MiniMax-M2.7", map[string]interface{}{
		"stream_callback": callback,
	})
	if err != nil {
		t.Fatalf("Chat() error: %v", err)
	}
	if resp.Content != "Hello from MiniMax!" {
		t.Errorf("Content = %q, want %q", resp.Content, "Hello from MiniMax!")
	}
	if accumulated != "Hello from MiniMax!" {
		t.Errorf("accumulated = %q, want %q", accumulated, "Hello from MiniMax!")
	}
}

func TestCreateProvider_MiniMax(t *testing.T) {
	// Test that CreateProvider correctly routes to MiniMax via config
	// This is a compile-time check that the config struct has the MiniMax field
	// and that CreateProvider handles the "minimax" provider name
	cfg := &config.Config{
		Agents: config.AgentsConfig{
			Defaults: config.AgentDefaults{
				Provider: "minimax",
				Model:    "MiniMax-M2.7",
			},
		},
		Providers: config.ProvidersConfig{
			MiniMax: config.ProviderConfig{
				APIKey:  "test-minimax-key",
				APIBase: "https://api.minimax.io/v1",
			},
		},
	}

	provider, err := CreateProvider(cfg)
	if err != nil {
		t.Fatalf("CreateProvider() error: %v", err)
	}
	httpProvider, ok := provider.(*HTTPProvider)
	if !ok {
		t.Fatalf("provider type = %T, want *HTTPProvider", provider)
	}
	if httpProvider.apiKey != "test-minimax-key" {
		t.Errorf("apiKey = %q, want %q", httpProvider.apiKey, "test-minimax-key")
	}
	if httpProvider.apiBase != "https://api.minimax.io/v1" {
		t.Errorf("apiBase = %q, want %q", httpProvider.apiBase, "https://api.minimax.io/v1")
	}
}

func TestCreateProvider_MiniMaxDefaultBaseURL(t *testing.T) {
	cfg := &config.Config{
		Agents: config.AgentsConfig{
			Defaults: config.AgentDefaults{
				Provider: "minimax",
				Model:    "MiniMax-M2.7",
			},
		},
		Providers: config.ProvidersConfig{
			MiniMax: config.ProviderConfig{
				APIKey: "test-minimax-key",
			},
		},
	}

	provider, err := CreateProvider(cfg)
	if err != nil {
		t.Fatalf("CreateProvider() error: %v", err)
	}
	httpProvider := provider.(*HTTPProvider)
	if httpProvider.apiBase != "https://api.minimax.io/v1" {
		t.Errorf("apiBase = %q, want default %q", httpProvider.apiBase, "https://api.minimax.io/v1")
	}
}

func TestCreateProvider_MiniMaxAlias(t *testing.T) {
	cfg := &config.Config{
		Agents: config.AgentsConfig{
			Defaults: config.AgentDefaults{
				Provider: "MiniMax",
				Model:    "MiniMax-M2.7",
			},
		},
		Providers: config.ProvidersConfig{
			MiniMax: config.ProviderConfig{
				APIKey: "test-minimax-key",
			},
		},
	}

	provider, err := CreateProvider(cfg)
	if err != nil {
		t.Fatalf("CreateProvider() with alias error: %v", err)
	}
	httpProvider := provider.(*HTTPProvider)
	if httpProvider.apiKey != "test-minimax-key" {
		t.Errorf("apiKey = %q, want %q", httpProvider.apiKey, "test-minimax-key")
	}
}
