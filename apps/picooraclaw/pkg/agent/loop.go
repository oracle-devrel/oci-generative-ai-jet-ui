// PicoClaw - Ultra-lightweight personal AI agent
// Inspired by and based on nanobot: https://github.com/HKUDS/nanobot
// License: MIT
//
// Copyright (c) 2026 PicoClaw contributors

package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"
	"unicode/utf8"

	"github.com/jasperan/picooraclaw/pkg/bus"
	"github.com/jasperan/picooraclaw/pkg/config"
	"github.com/jasperan/picooraclaw/pkg/constants"
	"github.com/jasperan/picooraclaw/pkg/logger"
	"github.com/jasperan/picooraclaw/pkg/providers"
	"github.com/jasperan/picooraclaw/pkg/session"
	"github.com/jasperan/picooraclaw/pkg/state"
	"github.com/jasperan/picooraclaw/pkg/tools"
	"github.com/jasperan/picooraclaw/pkg/utils"
)

type AgentLoop struct {
	bus                       *bus.MessageBus
	provider                  providers.LLMProvider
	workspace                 string
	model                     string
	contextWindow             int // Maximum context window size in tokens
	maxIterations             int
	summarizeMessageThreshold int // Trigger summarization after this many messages
	summarizeTokenPercent     int // Trigger summarization when history exceeds this % of context window
	sessions                  SessionManagerInterface
	state                     StateManagerInterface
	contextBuilder            *ContextBuilder
	tools                     *tools.ToolRegistry
	running                   atomic.Bool
	summarizing               sync.Map // Tracks which sessions are currently being summarized
	channelManager            channelManagerInterface
	emitter                   EventEmitter // Structured event emitter (defaults to NoopEmitter)
}

// channelManagerInterface allows the agent loop to query enabled channels.
type channelManagerInterface interface {
	GetEnabledChannels() []string
	HasChannel(name string) bool
}

// processOptions configures how a message is processed
type processOptions struct {
	SessionKey      string // Session identifier for history/context
	Channel         string // Target channel for tool execution
	ChatID          string // Target chat ID for tool execution
	UserMessage     string // User message content (may include prefix)
	DefaultResponse string // Response when LLM returns empty
	EnableSummary   bool   // Whether to trigger summarization
	SendResponse    bool   // Whether to send response via bus
	NoHistory       bool   // If true, don't load session history (for heartbeat)
	MessageID       string // Structured event message ID for this turn
}

// createToolRegistry creates a tool registry with common tools.
// This is shared between main agent and subagents.
func createToolRegistry(workspace string, restrict bool, cfg *config.Config, msgBus *bus.MessageBus) *tools.ToolRegistry {
	registry := tools.NewToolRegistry()

	// File system tools
	registry.Register(tools.NewReadFileTool(workspace, restrict))
	registry.Register(tools.NewWriteFileTool(workspace, restrict))
	registry.Register(tools.NewListDirTool(workspace, restrict))
	registry.Register(tools.NewEditFileTool(workspace, restrict))
	registry.Register(tools.NewAppendFileTool(workspace, restrict))

	// Shell execution
	registry.Register(tools.NewExecTool(workspace, restrict))

	if searchTool := tools.NewWebSearchTool(tools.WebSearchToolOptions{
		BraveAPIKey:          cfg.Tools.Web.Brave.APIKey,
		BraveMaxResults:      cfg.Tools.Web.Brave.MaxResults,
		BraveEnabled:         cfg.Tools.Web.Brave.Enabled,
		DuckDuckGoMaxResults: cfg.Tools.Web.DuckDuckGo.MaxResults,
		DuckDuckGoEnabled:    cfg.Tools.Web.DuckDuckGo.Enabled,
		PerplexityAPIKey:     cfg.Tools.Web.Perplexity.APIKey,
		PerplexityMaxResults: cfg.Tools.Web.Perplexity.MaxResults,
		PerplexityEnabled:    cfg.Tools.Web.Perplexity.Enabled,
	}); searchTool != nil {
		registry.Register(searchTool)
	}
	registry.Register(tools.NewWebFetchTool(50000))

	// Hardware tools (I2C, SPI) - Linux only, returns error on other platforms
	registry.Register(tools.NewI2CTool())
	registry.Register(tools.NewSPITool())

	// Message tool - available to both agent and subagent
	// Subagent uses it to communicate directly with user
	messageTool := tools.NewMessageTool()
	messageTool.SetSendCallback(func(channel, chatID, content string) error {
		msgBus.PublishOutbound(bus.OutboundMessage{
			Channel: channel,
			ChatID:  chatID,
			Content: content,
		})
		return nil
	})
	registry.Register(messageTool)

	return registry
}

func NewAgentLoop(cfg *config.Config, msgBus *bus.MessageBus, provider providers.LLMProvider) *AgentLoop {
	workspace := cfg.WorkspacePath()
	os.MkdirAll(workspace, 0755)

	restrict := cfg.Agents.Defaults.RestrictToWorkspace

	// Create tool registry for main agent
	toolsRegistry := createToolRegistry(workspace, restrict, cfg, msgBus)

	// Create subagent manager with its own tool registry
	subagentManager := tools.NewSubagentManager(provider, cfg.Agents.Defaults.Model, workspace, msgBus)
	subagentTools := createToolRegistry(workspace, restrict, cfg, msgBus)
	// Subagent doesn't need spawn/subagent tools to avoid recursion
	subagentManager.SetTools(subagentTools)

	// Register spawn tool (for main agent)
	spawnTool := tools.NewSpawnTool(subagentManager)
	toolsRegistry.Register(spawnTool)

	// Register subagent tool (synchronous execution)
	subagentTool := tools.NewSubagentTool(subagentManager)
	toolsRegistry.Register(subagentTool)

	sessionsManager := session.NewSessionManager(filepath.Join(workspace, "sessions"))

	// Create state manager for atomic state persistence
	stateManager := state.NewManager(workspace)

	// Create context builder and set tools registry
	contextBuilder := NewContextBuilder(workspace)
	contextBuilder.SetToolsRegistry(toolsRegistry)

	// Register write_daily_note with the file-based memory store
	toolsRegistry.Register(tools.NewWriteDailyNoteTool(contextBuilder.GetMemoryStore()))

	return newAgentLoop(cfg, msgBus, provider, sessionsManager, stateManager, contextBuilder, toolsRegistry)
}

// NewAgentLoopWithStores creates an AgentLoop with custom storage backends.
// Used when Oracle stores replace the default file-based stores.
func NewAgentLoopWithStores(cfg *config.Config, msgBus *bus.MessageBus, provider providers.LLMProvider, sessions SessionManagerInterface, stateStore StateManagerInterface, memoryStore MemoryStoreInterface) *AgentLoop {
	workspace := cfg.WorkspacePath()
	os.MkdirAll(workspace, 0755)

	restrict := cfg.Agents.Defaults.RestrictToWorkspace

	toolsRegistry := createToolRegistry(workspace, restrict, cfg, msgBus)

	subagentManager := tools.NewSubagentManager(provider, cfg.Agents.Defaults.Model, workspace, msgBus)
	subagentTools := createToolRegistry(workspace, restrict, cfg, msgBus)
	subagentManager.SetTools(subagentTools)

	spawnTool := tools.NewSpawnTool(subagentManager)
	toolsRegistry.Register(spawnTool)

	subagentTool := tools.NewSubagentTool(subagentManager)
	toolsRegistry.Register(subagentTool)

	contextBuilder := NewContextBuilder(workspace)
	contextBuilder.SetToolsRegistry(toolsRegistry)

	// Use Oracle memory store for context building if provided
	if memoryStore != nil {
		contextBuilder.SetMemoryStore(memoryStore)
	}

	return newAgentLoop(cfg, msgBus, provider, sessions, stateStore, contextBuilder, toolsRegistry)
}

// newAgentLoop creates the AgentLoop with configurable summarization thresholds.
func newAgentLoop(cfg *config.Config, msgBus *bus.MessageBus, provider providers.LLMProvider, sessions SessionManagerInterface, stateStore StateManagerInterface, contextBuilder *ContextBuilder, toolsRegistry *tools.ToolRegistry) *AgentLoop {
	summarizeMessageThreshold := cfg.Agents.Defaults.SummarizeMessageThreshold
	if summarizeMessageThreshold == 0 {
		summarizeMessageThreshold = 20
	}
	summarizeTokenPercent := cfg.Agents.Defaults.SummarizeTokenPercent
	if summarizeTokenPercent == 0 {
		summarizeTokenPercent = 75
	}

	return &AgentLoop{
		bus:                       msgBus,
		provider:                  provider,
		workspace:                 cfg.WorkspacePath(),
		model:                     cfg.Agents.Defaults.Model,
		contextWindow:             cfg.Agents.Defaults.MaxTokens,
		maxIterations:             cfg.Agents.Defaults.MaxToolIterations,
		summarizeMessageThreshold: summarizeMessageThreshold,
		summarizeTokenPercent:     summarizeTokenPercent,
		sessions:                  sessions,
		state:                     stateStore,
		contextBuilder:            contextBuilder,
		tools:                     toolsRegistry,
		summarizing:               sync.Map{},
		emitter:                   NoopEmitter{},
	}
}

// SetEventEmitter installs a structured event emitter. Passing nil resets the
// emitter to a NoopEmitter so call sites can always emit without nil checks.
func (al *AgentLoop) SetEventEmitter(e EventEmitter) {
	if e == nil {
		al.emitter = NoopEmitter{}
		return
	}
	al.emitter = e
}

// SetPromptStore sets an Oracle-backed prompt store on the context builder.
func (al *AgentLoop) SetPromptStore(store PromptStoreInterface) {
	al.contextBuilder.SetPromptStore(store)
}

// SetChannelManager sets the channel manager so the agent can query channel info.
func (al *AgentLoop) SetChannelManager(cm channelManagerInterface) {
	al.channelManager = cm
}

func (al *AgentLoop) Run(ctx context.Context) error {
	al.running.Store(true)

	for al.running.Load() {
		select {
		case <-ctx.Done():
			return nil
		default:
			msg, ok := al.bus.ConsumeInbound(ctx)
			if !ok {
				continue
			}

			response, err := al.processMessage(ctx, msg)
			if err != nil {
				response = fmt.Sprintf("Error processing message: %v", err)
			}

			if response != "" {
				// Check if the message tool already sent a response during this round.
				// If so, skip publishing to avoid duplicate messages to the user.
				alreadySent := false
				if tool, ok := al.tools.Get("message"); ok {
					if mt, ok := tool.(*tools.MessageTool); ok {
						alreadySent = mt.HasSentInRound()
					}
				}

				if !alreadySent {
					al.bus.PublishOutbound(bus.OutboundMessage{
						Channel: msg.Channel,
						ChatID:  msg.ChatID,
						Content: response,
					})
				}
			}
		}
	}

	return nil
}

func (al *AgentLoop) Stop() {
	al.running.Store(false)
}

func (al *AgentLoop) RegisterTool(tool tools.Tool) {
	al.tools.Register(tool)
}

// RecordLastChannel records the last active channel for this workspace.
// This uses the atomic state save mechanism to prevent data loss on crash.
func (al *AgentLoop) RecordLastChannel(channel string) error {
	return al.state.SetLastChannel(channel)
}

// RecordLastChatID records the last active chat ID for this workspace.
// This uses the atomic state save mechanism to prevent data loss on crash.
func (al *AgentLoop) RecordLastChatID(chatID string) error {
	return al.state.SetLastChatID(chatID)
}

func (al *AgentLoop) ProcessDirect(ctx context.Context, content, sessionKey string) (string, error) {
	return al.ProcessDirectWithChannel(ctx, content, sessionKey, "cli", "direct")
}

func (al *AgentLoop) ProcessDirectWithChannel(ctx context.Context, content, sessionKey, channel, chatID string) (string, error) {
	msg := bus.InboundMessage{
		Channel:    channel,
		SenderID:   "cron",
		ChatID:     chatID,
		Content:    content,
		SessionKey: sessionKey,
	}

	return al.processMessage(ctx, msg)
}

// ProcessHeartbeat processes a heartbeat request without session history.
// Each heartbeat is independent and doesn't accumulate context.
func (al *AgentLoop) ProcessHeartbeat(ctx context.Context, content, channel, chatID string) (string, error) {
	return al.runAgentLoop(ctx, processOptions{
		SessionKey:      "heartbeat",
		Channel:         channel,
		ChatID:          chatID,
		UserMessage:     content,
		DefaultResponse: "I've completed processing but have no response to give.",
		EnableSummary:   false,
		SendResponse:    false,
		NoHistory:       true, // Don't load session history for heartbeat
	})
}

func (al *AgentLoop) processMessage(ctx context.Context, msg bus.InboundMessage) (string, error) {
	// Add message preview to log (show full content for error messages)
	var logContent string
	if strings.Contains(msg.Content, "Error:") || strings.Contains(msg.Content, "error") {
		logContent = msg.Content // Full content for errors
	} else {
		logContent = utils.Truncate(msg.Content, 80)
	}
	logger.InfoCF("agent", fmt.Sprintf("Processing message from %s:%s: %s", msg.Channel, msg.SenderID, logContent),
		map[string]interface{}{
			"channel":     msg.Channel,
			"chat_id":     msg.ChatID,
			"sender_id":   msg.SenderID,
			"session_key": msg.SessionKey,
		})

	// Snapshot the emitter once per turn so all emissions use the same instance,
	// even if SetEventEmitter is called mid-turn. SetEventEmitter's contract says
	// it's safe to call before Start(); this snapshot protects any reader here.
	emitter := al.emitter
	if emitter == nil {
		emitter = NoopEmitter{}
	}

	// Generate a message ID for this turn. Tool events reuse the same ID so
	// consumers can correlate start/tool/end for a single user turn.
	messageID := fmt.Sprintf("m_%d", time.Now().UnixNano())

	emitter.Emit(Event{
		Type:      EventMessageStart,
		SessionID: msg.SessionKey,
		MessageID: messageID,
		Timestamp: time.Now(),
	})

	// Route system messages to processSystemMessage
	if msg.Channel == "system" {
		result, err := al.processSystemMessage(ctx, msg)
		if err != nil {
			emitter.Emit(Event{
				Type:      EventError,
				SessionID: msg.SessionKey,
				MessageID: messageID,
				Error:     err.Error(),
				Timestamp: time.Now(),
			})
			return result, err
		}
		emitter.Emit(Event{
			Type:      EventMessageEnd,
			SessionID: msg.SessionKey,
			MessageID: messageID,
			Text:      result,
			Timestamp: time.Now(),
		})
		return result, nil
	}

	// Check for slash commands
	if response, handled := al.handleCommand(ctx, msg); handled {
		emitter.Emit(Event{
			Type:      EventMessageEnd,
			SessionID: msg.SessionKey,
			MessageID: messageID,
			Text:      response,
			Timestamp: time.Now(),
		})
		return response, nil
	}

	// Process as user message
	result, err := al.runAgentLoop(ctx, processOptions{
		SessionKey:      msg.SessionKey,
		Channel:         msg.Channel,
		ChatID:          msg.ChatID,
		UserMessage:     msg.Content,
		DefaultResponse: "I've completed processing but have no response to give.",
		EnableSummary:   true,
		SendResponse:    false,
		MessageID:       messageID,
	})
	if err != nil {
		emitter.Emit(Event{
			Type:      EventError,
			SessionID: msg.SessionKey,
			MessageID: messageID,
			Error:     err.Error(),
			Timestamp: time.Now(),
		})
		return result, err
	}
	emitter.Emit(Event{
		Type:      EventMessageEnd,
		SessionID: msg.SessionKey,
		MessageID: messageID,
		Text:      result,
		Timestamp: time.Now(),
	})
	return result, nil
}

func (al *AgentLoop) processSystemMessage(ctx context.Context, msg bus.InboundMessage) (string, error) {
	// Verify this is a system message
	if msg.Channel != "system" {
		return "", fmt.Errorf("processSystemMessage called with non-system message channel: %s", msg.Channel)
	}

	logger.InfoCF("agent", "Processing system message",
		map[string]interface{}{
			"sender_id": msg.SenderID,
			"chat_id":   msg.ChatID,
		})

	// Parse origin channel from chat_id (format: "channel:chat_id")
	var originChannel string
	if idx := strings.Index(msg.ChatID, ":"); idx > 0 {
		originChannel = msg.ChatID[:idx]
	} else {
		// Fallback
		originChannel = "cli"
	}

	// Extract subagent result from message content
	// Format: "Task 'label' completed.\n\nResult:\n<actual content>"
	content := msg.Content
	if idx := strings.Index(content, "Result:\n"); idx >= 0 {
		content = content[idx+8:] // Extract just the result part
	}

	// Skip internal channels - only log, don't send to user
	if constants.IsInternalChannel(originChannel) {
		logger.InfoCF("agent", "Subagent completed (internal channel)",
			map[string]interface{}{
				"sender_id":   msg.SenderID,
				"content_len": len(content),
				"channel":     originChannel,
			})
		return "", nil
	}

	// Agent acts as dispatcher only - subagent handles user interaction via message tool
	// Don't forward result here, subagent should use message tool to communicate with user
	logger.InfoCF("agent", "Subagent completed",
		map[string]interface{}{
			"sender_id":   msg.SenderID,
			"channel":     originChannel,
			"content_len": len(content),
		})

	// Agent only logs, does not respond to user
	return "", nil
}

// runAgentLoop is the core message processing logic.
// It handles context building, LLM calls, tool execution, and response handling.
func (al *AgentLoop) runAgentLoop(ctx context.Context, opts processOptions) (string, error) {
	// 0. Record last channel for heartbeat notifications (skip internal channels)
	if opts.Channel != "" && opts.ChatID != "" {
		// Don't record internal channels (cli, system, subagent)
		if !constants.IsInternalChannel(opts.Channel) {
			channelKey := fmt.Sprintf("%s:%s", opts.Channel, opts.ChatID)
			if err := al.RecordLastChannel(channelKey); err != nil {
				logger.WarnCF("agent", "Failed to record last channel: %v", map[string]interface{}{"error": err.Error()})
			}
		}
	}

	// 1. Reset per-round send tracker on the message tool
	if tool, ok := al.tools.Get("message"); ok {
		if mt, ok := tool.(*tools.MessageTool); ok {
			mt.ResetSentInRound()
		}
	}

	// 2. Build messages (skip history for heartbeat)
	var history []providers.Message
	var summary string
	if !opts.NoHistory {
		history = al.sessions.GetHistory(opts.SessionKey)
		summary = al.sessions.GetSummary(opts.SessionKey)
	}
	messages := al.contextBuilder.BuildMessages(
		history,
		summary,
		opts.UserMessage,
		nil,
		opts.Channel,
		opts.ChatID,
	)

	// 3. Save user message to session
	al.sessions.AddMessage(opts.SessionKey, "user", opts.UserMessage)

	// 4. Run LLM iteration loop
	finalContent, iteration, err := al.runLLMIteration(ctx, messages, opts)
	if err != nil {
		return "", err
	}

	// If last tool had ForUser content and we already sent it, we might not need to send final response
	// This is controlled by the tool's Silent flag and ForUser content

	// 5. Handle empty response
	if finalContent == "" {
		finalContent = opts.DefaultResponse
	}

	// 6. Save final assistant message to session
	al.sessions.AddMessage(opts.SessionKey, "assistant", finalContent)
	al.sessions.Save(opts.SessionKey)

	// 7. Optional: summarization
	if opts.EnableSummary {
		al.maybeSummarize(opts.SessionKey)
	}

	// 8. Optional: send response via bus
	if opts.SendResponse {
		al.bus.PublishOutbound(bus.OutboundMessage{
			Channel: opts.Channel,
			ChatID:  opts.ChatID,
			Content: finalContent,
		})
	}

	// 9. Log response
	responsePreview := utils.Truncate(finalContent, 120)
	logger.InfoCF("agent", fmt.Sprintf("Response: %s", responsePreview),
		map[string]interface{}{
			"session_key":  opts.SessionKey,
			"iterations":   iteration,
			"final_length": len(finalContent),
		})

	return finalContent, nil
}

// runLLMIteration executes the LLM call loop with tool handling.
// Returns the final content, iteration count, and any error.
func (al *AgentLoop) runLLMIteration(ctx context.Context, messages []providers.Message, opts processOptions) (string, int, error) {
	iteration := 0
	var finalContent string

	// Track recent tool calls to detect infinite loops (M5)
	type toolCallKey struct {
		Name string
		Args string
	}
	recentToolCalls := make(map[toolCallKey]int)

	for iteration < al.maxIterations {
		iteration++

		logger.DebugCF("agent", "LLM iteration",
			map[string]interface{}{
				"iteration": iteration,
				"max":       al.maxIterations,
			})

		// Warn when approaching iteration limit
		if iteration >= al.maxIterations*80/100 {
			logger.WarnCF("agent", "Approaching max iterations limit",
				map[string]interface{}{"iteration": iteration, "max": al.maxIterations})
		}

		// Build tool definitions
		providerToolDefs := al.tools.ToProviderDefs()

		// Log LLM request details
		logger.DebugCF("agent", "LLM request",
			map[string]interface{}{
				"iteration":         iteration,
				"model":             al.model,
				"messages_count":    len(messages),
				"tools_count":       len(providerToolDefs),
				"max_tokens":        8192,
				"temperature":       0.7,
				"system_prompt_len": len(messages[0].Content),
			})

		// Log full messages (detailed)
		logger.DebugCF("agent", "Full LLM request",
			map[string]interface{}{
				"iteration":     iteration,
				"messages_json": formatMessagesForLog(messages),
				"tools_json":    formatToolsForLog(providerToolDefs),
			})

		// Call LLM with retry on context/token errors, rate limits, and transient failures
		var response *providers.LLMResponse
		var err error
		maxRetries := 3
		for retry := 0; retry <= maxRetries; retry++ {
			response, err = al.provider.Chat(ctx, messages, providerToolDefs, al.model, map[string]interface{}{
				"max_tokens":  8192,
				"temperature": 0.7,
			})

			if err == nil {
				break
			}

			errMsg := strings.ToLower(err.Error())
			isContextError := strings.Contains(errMsg, "token") ||
				strings.Contains(errMsg, "context") ||
				strings.Contains(errMsg, "invalidparameter") ||
				strings.Contains(errMsg, "length")
			isRateLimit := strings.Contains(errMsg, "429") || strings.Contains(errMsg, "rate") || strings.Contains(errMsg, "quota")
			isTransient := strings.Contains(errMsg, "502") || strings.Contains(errMsg, "503") || strings.Contains(errMsg, "timeout")

			if isRateLimit && retry < maxRetries {
				backoff := time.Duration(1<<uint(retry)) * 5 * time.Second
				logger.WarnCF("agent", "Rate limited, backing off",
					map[string]interface{}{"backoff": backoff.String(), "retry": retry})
				time.Sleep(backoff)
				continue
			}
			if isTransient && retry < maxRetries {
				backoff := time.Duration(1<<uint(retry)) * 2 * time.Second
				logger.WarnCF("agent", "Transient error, retrying",
					map[string]interface{}{"backoff": backoff.String(), "retry": retry})
				time.Sleep(backoff)
				continue
			}

			if isContextError && retry < maxRetries {
				logger.WarnCF("agent", "Context window error, compressing history",
					map[string]interface{}{"error": err.Error(), "retry": retry})

				// Progressive compression strategy:
				// Retry 0: Remove tool definitions (often the largest component)
				// Retry 1: Keep system prompt + last 25% of messages
				// Retry 2: Keep system prompt + last 2 messages (most aggressive)
				switch retry {
				case 0:
					// First retry: remove tool definitions to free space
					providerToolDefs = nil
					logger.InfoCF("agent", "Retry 0: removed tool definitions to free context space", nil)
				case 1:
					// Second retry: keep system prompt + last 25% of messages
					if len(messages) > 4 {
						quarterIdx := len(messages) - len(messages)/4
						if quarterIdx < 2 {
							quarterIdx = 2
						}
						keep := make([]providers.Message, 0, 1+len(messages)-quarterIdx)
						keep = append(keep, messages[0])
						keep = append(keep, messages[quarterIdx:]...)

						messages = keep
						logger.InfoCF("agent", "Retry 1: kept system prompt + recent messages",
							map[string]interface{}{"kept": len(keep)})
					}
				case 2:
					// Third retry: most aggressive - system prompt + last 2 messages
					if len(messages) > 3 {
						keep := make([]providers.Message, 0, 3)
						keep = append(keep, messages[0])
						keep = append(keep, messages[len(messages)-2:]...)
						messages = keep
						logger.InfoCF("agent", "Retry 2: kept system prompt + last 2 messages",
							map[string]interface{}{"kept": len(keep)})
					}
				}
				continue
			}
			break
		}

		if err != nil {
			logger.ErrorCF("agent", "LLM call failed",
				map[string]interface{}{
					"iteration": iteration,
					"error":     err.Error(),
				})
			return "", iteration, fmt.Errorf("LLM call failed: %w", err)
		}

		// Check if no tool calls - we're done
		if len(response.ToolCalls) == 0 {
			finalContent = response.Content
			// Fallback to reasoning content if main content is empty (#992)
			if finalContent == "" && response.ReasoningContent != "" {
				finalContent = response.ReasoningContent
			}
			logger.InfoCF("agent", "LLM response without tool calls (direct answer)",
				map[string]interface{}{
					"iteration":     iteration,
					"content_chars": len(finalContent),
				})
			break
		}

		// Log tool calls
		toolNames := make([]string, 0, len(response.ToolCalls))
		for _, tc := range response.ToolCalls {
			toolNames = append(toolNames, tc.Name)
		}
		logger.InfoCF("agent", "LLM requested tool calls",
			map[string]interface{}{
				"tools":     toolNames,
				"count":     len(response.ToolCalls),
				"iteration": iteration,
			})

		// Build assistant message with tool calls
		assistantMsg := providers.Message{
			Role:    "assistant",
			Content: response.Content,
		}
		for _, tc := range response.ToolCalls {
			argumentsJSON, _ := json.Marshal(tc.Arguments)
			assistantMsg.ToolCalls = append(assistantMsg.ToolCalls, providers.ToolCall{
				ID:   tc.ID,
				Type: "function",
				Function: &providers.FunctionCall{
					Name:      tc.Name,
					Arguments: string(argumentsJSON),
				},
			})
		}
		messages = append(messages, assistantMsg)

		// Save assistant message with tool calls to session
		al.sessions.AddFullMessage(opts.SessionKey, assistantMsg)

		// Execute tool calls in parallel (#1070)
		type indexedToolResult struct {
			result *tools.ToolResult
			tc     providers.ToolCall
			loopHit bool   // true if this call was a loop detection hit
			loopMsg string // warning message for loop detection
		}

		toolResults := make([]indexedToolResult, len(response.ToolCalls))
		var wg sync.WaitGroup

		for i, tc := range response.ToolCalls {
			toolResults[i].tc = tc

			// Check for repeated identical tool calls (loop detection) - must be serial
			argsJSON, _ := json.Marshal(tc.Arguments)
			key := toolCallKey{Name: tc.Name, Args: string(argsJSON)}
			recentToolCalls[key]++
			if recentToolCalls[key] > 2 {
				toolResults[i].loopHit = true
				toolResults[i].loopMsg = fmt.Sprintf("Warning: tool '%s' with these arguments was already called %d times. Try a different approach.", tc.Name, recentToolCalls[key]-1)
				continue
			}

			wg.Add(1)
			go func(idx int, tc providers.ToolCall) {
				defer wg.Done()

				argsJSON, _ := json.Marshal(tc.Arguments)
				argsPreview := utils.Truncate(string(argsJSON), 200)
				logger.InfoCF("agent", fmt.Sprintf("Tool call: %s(%s)", tc.Name, argsPreview),
					map[string]interface{}{
						"tool":      tc.Name,
						"iteration": iteration,
					})

				// Create async callback for tools that implement AsyncExecutor.
				// Sends ForUser content directly to user and publishes ForLLM as inbound.
				asyncCallback := func(_ context.Context, result *tools.ToolResult) {
					if !result.Silent && result.ForUser != "" {
						al.bus.PublishOutbound(bus.OutboundMessage{
							Channel: opts.Channel,
							ChatID:  opts.ChatID,
							Content: result.ForUser,
						})
					}

					content := result.ForLLM
					if content == "" && result.Err != nil {
						content = result.Err.Error()
					}
					if content == "" {
						return
					}

					logger.InfoCF("agent", "Async tool completed, publishing result",
						map[string]interface{}{
							"tool":        tc.Name,
							"content_len": len(content),
							"channel":     opts.Channel,
						})

					al.bus.PublishInbound(bus.InboundMessage{
						Channel:  "system",
						SenderID: fmt.Sprintf("async:%s", tc.Name),
						ChatID:   fmt.Sprintf("%s:%s", opts.Channel, opts.ChatID),
						Content:  content,
					})
				}

				// Emit tool_call_start before execution. Snapshot emitter once to
				// keep this turn's emissions consistent even if SetEventEmitter
				// races (contract says don't, but cheap insurance).
				emitter := al.emitter
				if emitter == nil {
					emitter = NoopEmitter{}
				}
				emitter.Emit(Event{
					Type:       EventToolCallStart,
					SessionID:  opts.SessionKey,
					MessageID:  opts.MessageID,
					ToolCallID: tc.ID,
					ToolName:   tc.Name,
					Args:       tc.Arguments,
					Timestamp:  time.Now(),
				})

				toolResult := al.tools.ExecuteWithContext(ctx, tc.Name, tc.Arguments, opts.Channel, opts.ChatID, asyncCallback)
				toolResults[idx].result = toolResult

				// Build result + ok fields for tool_call_end.
				var resultStr string
				ok := true
				if toolResult != nil && toolResult.Err != nil {
					resultStr = toolResult.Err.Error()
					ok = false
				} else if toolResult != nil {
					resultStr = toolResult.ForLLM
					if resultStr == "" {
						resultStr = toolResult.ForUser
					}
				}
				if len(resultStr) > 4096 {
					i := 4096
					for i > 0 && !utf8.RuneStart(resultStr[i]) {
						i--
					}
					resultStr = resultStr[:i] + "…[truncated]"
				}
				emitter.Emit(Event{
					Type:       EventToolCallEnd,
					SessionID:  opts.SessionKey,
					MessageID:  opts.MessageID,
					ToolCallID: tc.ID,
					ToolName:   tc.Name,
					Result:     resultStr,
					OK:         &ok,
					Timestamp:  time.Now(),
				})
			}(i, tc)
		}
		wg.Wait()

		// Process results in original order (send to user, save to session)
		for _, r := range toolResults {
			if r.loopHit {
				toolResultMsg := providers.Message{
					Role:       "tool",
					Content:    r.loopMsg,
					ToolCallID: r.tc.ID,
				}
				messages = append(messages, toolResultMsg)
				al.sessions.AddFullMessage(opts.SessionKey, toolResultMsg)
				continue
			}

			// Send ForUser content to user immediately if not Silent
			if !r.result.Silent && r.result.ForUser != "" && opts.SendResponse {
				al.bus.PublishOutbound(bus.OutboundMessage{
					Channel: opts.Channel,
					ChatID:  opts.ChatID,
					Content: r.result.ForUser,
				})
				logger.DebugCF("agent", "Sent tool result to user",
					map[string]interface{}{
						"tool":        r.tc.Name,
						"content_len": len(r.result.ForUser),
					})
			}

			// Determine content for LLM based on tool result
			contentForLLM := r.result.ForLLM
			if contentForLLM == "" && r.result.Err != nil {
				contentForLLM = r.result.Err.Error()
			}

			toolResultMsg := providers.Message{
				Role:       "tool",
				Content:    contentForLLM,
				ToolCallID: r.tc.ID,
			}
			messages = append(messages, toolResultMsg)

			// Save tool result message to session
			al.sessions.AddFullMessage(opts.SessionKey, toolResultMsg)
		}
	}

	return finalContent, iteration, nil
}


// maybeSummarize triggers summarization if the session history exceeds thresholds.
func (al *AgentLoop) maybeSummarize(sessionKey string) {
	newHistory := al.sessions.GetHistory(sessionKey)
	tokenEstimate := al.estimateTokens(newHistory)
	threshold := al.contextWindow * al.summarizeTokenPercent / 100

	if len(newHistory) > al.summarizeMessageThreshold || tokenEstimate > threshold {
		if _, loading := al.summarizing.LoadOrStore(sessionKey, true); !loading {
			go func() {
				defer al.summarizing.Delete(sessionKey)
				defer func() {
					if r := recover(); r != nil {
						logger.ErrorCF("agent", "Summarization panicked",
							map[string]interface{}{"session": sessionKey, "panic": fmt.Sprintf("%v", r)})
					}
				}()
				al.summarizeSession(sessionKey)
			}()
		}
	}
}

// GetStartupInfo returns information about loaded tools and skills for logging.
func (al *AgentLoop) GetStartupInfo() map[string]interface{} {
	info := make(map[string]interface{})

	// Tools info
	tools := al.tools.List()
	info["tools"] = map[string]interface{}{
		"count": len(tools),
		"names": tools,
	}

	// Skills info
	info["skills"] = al.contextBuilder.GetSkillsInfo()

	return info
}

// formatMessagesForLog formats messages for logging
func formatMessagesForLog(messages []providers.Message) string {
	if len(messages) == 0 {
		return "[]"
	}

	var result string
	result += "[\n"
	for i, msg := range messages {
		result += fmt.Sprintf("  [%d] Role: %s\n", i, msg.Role)
		if len(msg.ToolCalls) > 0 {
			result += "  ToolCalls:\n"
			for _, tc := range msg.ToolCalls {
				result += fmt.Sprintf("    - ID: %s, Type: %s, Name: %s\n", tc.ID, tc.Type, tc.Name)
				if tc.Function != nil {
					result += fmt.Sprintf("      Arguments: %s\n", utils.Truncate(tc.Function.Arguments, 200))
				}
			}
		}
		if msg.Content != "" {
			content := utils.Truncate(msg.Content, 200)
			result += fmt.Sprintf("  Content: %s\n", content)
		}
		if msg.ToolCallID != "" {
			result += fmt.Sprintf("  ToolCallID: %s\n", msg.ToolCallID)
		}
		result += "\n"
	}
	result += "]"
	return result
}

// formatToolsForLog formats tool definitions for logging
func formatToolsForLog(tools []providers.ToolDefinition) string {
	if len(tools) == 0 {
		return "[]"
	}

	var result string
	result += "[\n"
	for i, tool := range tools {
		result += fmt.Sprintf("  [%d] Type: %s, Name: %s\n", i, tool.Type, tool.Function.Name)
		result += fmt.Sprintf("      Description: %s\n", tool.Function.Description)
		if len(tool.Function.Parameters) > 0 {
			result += fmt.Sprintf("      Parameters: %s\n", utils.Truncate(fmt.Sprintf("%v", tool.Function.Parameters), 200))
		}
	}
	result += "]"
	return result
}

// summarizeSession summarizes the conversation history for a session.
func (al *AgentLoop) summarizeSession(sessionKey string) {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	history := al.sessions.GetHistory(sessionKey)
	summary := al.sessions.GetSummary(sessionKey)

	// Keep last 4 messages for continuity
	if len(history) <= 4 {
		return
	}

	toSummarize := history[:len(history)-4]

	// Oversized Message Guard
	// Skip messages larger than 50% of context window to prevent summarizer overflow
	maxMessageTokens := al.contextWindow / 2
	validMessages := make([]providers.Message, 0)
	omitted := false

	for _, m := range toSummarize {
		if m.Role != "user" && m.Role != "assistant" {
			continue
		}
		// Estimate tokens for this message
		msgTokens := len(m.Content) / 4
		if msgTokens > maxMessageTokens {
			omitted = true
			continue
		}
		validMessages = append(validMessages, m)
	}

	if len(validMessages) == 0 {
		return
	}

	// Multi-Part Summarization
	// Split into two parts if history is significant
	var finalSummary string
	if len(validMessages) > 10 {
		mid := len(validMessages) / 2
		part1 := validMessages[:mid]
		part2 := validMessages[mid:]

		s1, _ := al.summarizeBatch(ctx, part1, "")
		s2, _ := al.summarizeBatch(ctx, part2, "")

		// Merge them
		mergePrompt := fmt.Sprintf("Merge these two conversation summaries into one cohesive summary:\n\n1: %s\n\n2: %s", s1, s2)
		resp, err := al.provider.Chat(ctx, []providers.Message{{Role: "user", Content: mergePrompt}}, nil, al.model, map[string]interface{}{
			"max_tokens":  1024,
			"temperature": 0.3,
		})
		if err == nil {
			finalSummary = resp.Content
		} else {
			finalSummary = s1 + " " + s2
		}
	} else {
		finalSummary, _ = al.summarizeBatch(ctx, validMessages, summary)
	}

	if omitted && finalSummary != "" {
		finalSummary += "\n[Note: Some oversized messages were omitted from this summary for efficiency.]"
	}

	if finalSummary != "" {
		al.sessions.SetSummary(sessionKey, finalSummary)
		al.sessions.TruncateHistory(sessionKey, 4)
		al.sessions.Save(sessionKey)
	}
}

// summarizeBatch summarizes a batch of messages.
func (al *AgentLoop) summarizeBatch(ctx context.Context, batch []providers.Message, existingSummary string) (string, error) {
	prompt := "Provide a concise summary of this conversation segment, preserving core context and key points.\n"
	if existingSummary != "" {
		prompt += "Existing context: " + existingSummary + "\n"
	}
	prompt += "\nCONVERSATION:\n"
	for _, m := range batch {
		prompt += fmt.Sprintf("%s: %s\n", m.Role, m.Content)
	}

	response, err := al.provider.Chat(ctx, []providers.Message{{Role: "user", Content: prompt}}, nil, al.model, map[string]interface{}{
		"max_tokens":  1024,
		"temperature": 0.3,
	})
	if err != nil {
		return "", err
	}
	return response.Content, nil
}

// estimateTokens estimates the number of tokens in a message list.
// Uses model-aware character-per-token ratios for better accuracy.
// Accounts for message structure overhead (~4 tokens per message).
func (al *AgentLoop) estimateTokens(messages []providers.Message) int {
	totalChars := 0
	for _, m := range messages {
		totalChars += utf8.RuneCountInString(m.Content)
		// Account for message structure overhead (~4 tokens per message)
		totalChars += 16
	}
	// Model-specific ratios (chars per token)
	ratio := 4.0 // conservative default
	model := strings.ToLower(al.model)
	switch {
	case strings.Contains(model, "claude"):
		ratio = 3.5
	case strings.Contains(model, "gpt"):
		ratio = 3.5
	case strings.Contains(model, "qwen"):
		ratio = 2.5
	case strings.Contains(model, "llama"):
		ratio = 3.0
	case strings.Contains(model, "deepseek"):
		ratio = 2.8
	}
	return int(float64(totalChars) / ratio)
}

// handleCommand handles slash commands like /show, /list, /switch.
// Returns the response and true if the message was a command, false otherwise.
func (al *AgentLoop) handleCommand(_ context.Context, msg bus.InboundMessage) (string, bool) {
	content := strings.TrimSpace(msg.Content)
	if !strings.HasPrefix(content, "/") {
		return "", false
	}

	parts := strings.Fields(content)
	if len(parts) == 0 {
		return "", false
	}

	cmd := parts[0]
	args := parts[1:]

	switch cmd {
	case "/show":
		if len(args) < 1 {
			return "Usage: /show [model|channel]", true
		}
		switch args[0] {
		case "model":
			return fmt.Sprintf("Current model: %s", al.model), true
		case "channel":
			return fmt.Sprintf("Current channel: %s", msg.Channel), true
		default:
			return fmt.Sprintf("Unknown show target: %s", args[0]), true
		}

	case "/list":
		if len(args) < 1 {
			return "Usage: /list [models|channels]", true
		}
		switch args[0] {
		case "models":
			return fmt.Sprintf("Configured model: %s (change in config.json)", al.model), true
		case "channels":
			if al.channelManager == nil {
				return "Channel manager not initialized", true
			}
			channels := al.channelManager.GetEnabledChannels()
			if len(channels) == 0 {
				return "No channels enabled", true
			}
			return fmt.Sprintf("Enabled channels: %s", strings.Join(channels, ", ")), true
		default:
			return fmt.Sprintf("Unknown list target: %s", args[0]), true
		}

	case "/switch":
		if len(args) < 3 || args[1] != "to" {
			return "Usage: /switch [model|channel] to <name>", true
		}
		target := args[0]
		value := args[2]

		switch target {
		case "model":
			oldModel := al.model
			al.model = value
			return fmt.Sprintf("Switched model from %s to %s", oldModel, value), true
		case "channel":
			if al.channelManager == nil {
				return "Channel manager not initialized", true
			}
			if !al.channelManager.HasChannel(value) && value != "cli" {
				return fmt.Sprintf("Channel '%s' not found or not enabled", value), true
			}
			return fmt.Sprintf("Switched target channel to %s", value), true
		default:
			return fmt.Sprintf("Unknown switch target: %s", target), true
		}
	}

	return "", false
}
