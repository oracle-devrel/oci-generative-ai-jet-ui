package web

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/jasperan/picooraclaw/pkg/bus"
)

type chatRequest struct {
	SessionID string `json:"session_id"`
	Text      string `json:"text"`
	Workspace string `json:"workspace,omitempty"`
}

type chatResponse struct {
	MessageID string `json:"message_id"`
}

func (c *Channel) registerRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/v1/chat", c.handleChat)
	mux.HandleFunc("/v1/events", c.handleEvents)
	mux.HandleFunc("/v1/sessions", c.handleSessions)
	mux.HandleFunc("/v1/memory", c.handleMemory)
}

func (c *Channel) authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if c.cfg.Token != "" {
			if r.Header.Get("Authorization") != "Bearer "+c.cfg.Token {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

func (c *Channel) handleEvents(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	sessionID := r.URL.Query().Get("session_id")
	if sessionID == "" {
		http.Error(w, "session_id required", http.StatusBadRequest)
		return
	}
	from := r.URL.Query().Get("from")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")

	sub := c.broker.Subscribe(sessionID, from)
	defer c.broker.Unsubscribe(sub)

	fmt.Fprintf(w, ": ping\n\n")
	flusher.Flush()

	enc := json.NewEncoder(w)
	for {
		select {
		case ev, ok := <-sub.C:
			if !ok {
				return
			}
			fmt.Fprint(w, "data: ")
			_ = enc.Encode(ev) // writes JSON + newline
			fmt.Fprint(w, "\n")
			flusher.Flush()
		case <-r.Context().Done():
			return
		}
	}
}

func (c *Channel) handleChat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req chatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}
	if req.SessionID == "" || req.Text == "" {
		http.Error(w, "session_id and text are required", http.StatusBadRequest)
		return
	}

	meta := map[string]string{}
	if req.Workspace != "" {
		meta["workspace"] = req.Workspace
	}

	c.bus.PublishInbound(bus.InboundMessage{
		Channel:    "web",
		SenderID:   "web-user",
		ChatID:     req.SessionID,
		Content:    req.Text,
		SessionKey: req.SessionID,
		Metadata:   meta,
	})

	mid := fmt.Sprintf("m_%d", time.Now().UnixNano())
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	_ = json.NewEncoder(w).Encode(chatResponse{MessageID: mid})
}
func (c *Channel) handleSessions(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		list := []SessionInfo{}
		if c.sessions != nil {
			list = c.sessions.ListSessions()
		}
		if list == nil {
			list = []SessionInfo{}
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(list)
	case http.MethodPost:
		if c.sessions == nil {
			http.Error(w, "sessions not configured", http.StatusServiceUnavailable)
			return
		}
		var body struct {
			Title string `json:"title"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "invalid json", http.StatusBadRequest)
			return
		}
		if body.Title == "" {
			http.Error(w, "title required", http.StatusBadRequest)
			return
		}
		s, err := c.sessions.CreateSession(body.Title)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(s)
	case http.MethodDelete:
		if c.sessions == nil {
			http.Error(w, "sessions not configured", http.StatusServiceUnavailable)
			return
		}
		id := r.URL.Query().Get("id")
		if id == "" {
			http.Error(w, "id required", http.StatusBadRequest)
			return
		}
		if err := c.sessions.DeleteSession(id); err != nil {
			http.Error(w, err.Error(), http.StatusNotFound)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}
func (c *Channel) handleMemory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "application/json")

	if c.memory == nil {
		_, _ = w.Write([]byte("[]"))
		return
	}

	q := r.URL.Query().Get("q")
	limit := 20
	if v := r.URL.Query().Get("limit"); v != "" {
		// best-effort int parse; bad input falls back to default
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			limit = n
		}
	}

	results := c.memory.Search(q, limit)
	if results == nil {
		results = []MemoryResult{}
	}
	_ = json.NewEncoder(w).Encode(results)
}
