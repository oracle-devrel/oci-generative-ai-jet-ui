// PicoClaw - Ultra-lightweight personal AI agent
// Inspired by and based on nanobot: https://github.com/HKUDS/nanobot
// License: MIT
//
// Copyright (c) 2026 PicoClaw contributors

package channels

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/jasperan/picooraclaw/pkg/bus"
	"github.com/jasperan/picooraclaw/pkg/channels/web"
	"github.com/jasperan/picooraclaw/pkg/config"
	"github.com/jasperan/picooraclaw/pkg/constants"
	"github.com/jasperan/picooraclaw/pkg/logger"
)

type Manager struct {
	channels     map[string]Channel
	bus          *bus.MessageBus
	config       *config.Config
	dispatchTask *asyncTask
	mu           sync.RWMutex
}

type asyncTask struct {
	cancel context.CancelFunc
}

func NewManager(cfg *config.Config, messageBus *bus.MessageBus) (*Manager, error) {
	m := &Manager{
		channels: make(map[string]Channel),
		bus:      messageBus,
		config:   cfg,
	}

	if err := m.initChannels(); err != nil {
		return nil, err
	}

	return m, nil
}

func (m *Manager) initChannels() error {
	logger.InfoC("channels", "Initializing channel manager")

	// Data-driven channel initialization to reduce code duplication
	type channelEntry struct {
		name    string
		enabled bool
		factory func() (Channel, error)
	}

	entries := []channelEntry{
		{"telegram", m.config.Channels.Telegram.Enabled && m.config.Channels.Telegram.Token != "",
			func() (Channel, error) { return NewTelegramChannel(m.config.Channels.Telegram, m.bus) }},
		{"whatsapp", m.config.Channels.WhatsApp.Enabled && m.config.Channels.WhatsApp.BridgeURL != "",
			func() (Channel, error) { return NewWhatsAppChannel(m.config.Channels.WhatsApp, m.bus) }},
		{"feishu", m.config.Channels.Feishu.Enabled,
			func() (Channel, error) { return NewFeishuChannel(m.config.Channels.Feishu, m.bus) }},
		{"discord", m.config.Channels.Discord.Enabled && m.config.Channels.Discord.Token != "",
			func() (Channel, error) { return NewDiscordChannel(m.config.Channels.Discord, m.bus) }},
		{"maixcam", m.config.Channels.MaixCam.Enabled,
			func() (Channel, error) { return NewMaixCamChannel(m.config.Channels.MaixCam, m.bus) }},
		{"qq", m.config.Channels.QQ.Enabled,
			func() (Channel, error) { return NewQQChannel(m.config.Channels.QQ, m.bus) }},
		{"dingtalk", m.config.Channels.DingTalk.Enabled && m.config.Channels.DingTalk.ClientID != "",
			func() (Channel, error) { return NewDingTalkChannel(m.config.Channels.DingTalk, m.bus) }},
		{"slack", m.config.Channels.Slack.Enabled && m.config.Channels.Slack.BotToken != "",
			func() (Channel, error) { return NewSlackChannel(m.config.Channels.Slack, m.bus) }},
		{"line", m.config.Channels.LINE.Enabled && m.config.Channels.LINE.ChannelAccessToken != "",
			func() (Channel, error) { return NewLINEChannel(m.config.Channels.LINE, m.bus) }},
		{"onebot", m.config.Channels.OneBot.Enabled && m.config.Channels.OneBot.WSUrl != "",
			func() (Channel, error) { return NewOneBotChannel(m.config.Channels.OneBot, m.bus) }},
		{"web", m.config.Channels.Web.Enabled,
			func() (Channel, error) { return web.NewChannel(m.config.Channels.Web, m.bus) }},
	}

	for _, entry := range entries {
		if !entry.enabled {
			continue
		}
		logger.DebugCF("channels", fmt.Sprintf("Attempting to initialize %s channel", entry.name), nil)
		ch, err := entry.factory()
		if err != nil {
			logger.ErrorCF("channels", fmt.Sprintf("Failed to initialize %s channel", entry.name),
				map[string]interface{}{"error": err.Error()})
		} else {
			m.channels[entry.name] = ch
			logger.InfoCF("channels", fmt.Sprintf("%s channel enabled successfully", entry.name), nil)
		}
	}

	logger.InfoCF("channels", "Channel initialization completed", map[string]interface{}{
		"enabled_channels": len(m.channels),
	})

	return nil
}

func (m *Manager) StartAll(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(m.channels) == 0 {
		logger.WarnC("channels", "No channels enabled")
		return nil
	}

	logger.InfoC("channels", "Starting all channels")

	dispatchCtx, cancel := context.WithCancel(ctx)
	m.dispatchTask = &asyncTask{cancel: cancel}

	go m.dispatchOutbound(dispatchCtx)

	for name, channel := range m.channels {
		logger.InfoCF("channels", "Starting channel", map[string]interface{}{
			"channel": name,
		})
		if err := channel.Start(ctx); err != nil {
			logger.ErrorCF("channels", "Failed to start channel", map[string]interface{}{
				"channel": name,
				"error":   err.Error(),
			})
		}
	}

	logger.InfoC("channels", "All channels started")
	return nil
}

func (m *Manager) StopAll(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	logger.InfoC("channels", "Stopping all channels")

	if m.dispatchTask != nil {
		m.dispatchTask.cancel()
		m.dispatchTask = nil
	}

	for name, channel := range m.channels {
		logger.InfoCF("channels", "Stopping channel", map[string]interface{}{
			"channel": name,
		})
		if err := channel.Stop(ctx); err != nil {
			logger.ErrorCF("channels", "Error stopping channel", map[string]interface{}{
				"channel": name,
				"error":   err.Error(),
			})
		}
	}

	logger.InfoC("channels", "All channels stopped")
	return nil
}

func (m *Manager) dispatchOutbound(ctx context.Context) {
	logger.InfoC("channels", "Outbound dispatcher started")

	for {
		select {
		case <-ctx.Done():
			logger.InfoC("channels", "Outbound dispatcher stopped")
			return
		default:
			msg, ok := m.bus.SubscribeOutbound(ctx)
			if !ok {
				continue
			}

			// Silently skip internal channels
			if constants.IsInternalChannel(msg.Channel) {
				continue
			}

			m.mu.RLock()
			channel, exists := m.channels[msg.Channel]
			m.mu.RUnlock()

			if !exists {
				logger.WarnCF("channels", "Unknown channel for outbound message", map[string]interface{}{
					"channel": msg.Channel,
				})
				continue
			}

			// Send with a 30-second timeout to prevent one slow channel from blocking dispatch
			sendCtx, sendCancel := context.WithTimeout(ctx, 30*time.Second)
			if err := channel.Send(sendCtx, msg); err != nil {
				logger.ErrorCF("channels", "Error sending message to channel", map[string]interface{}{
					"channel": msg.Channel,
					"error":   err.Error(),
				})
			}
			sendCancel()
		}
	}
}

func (m *Manager) GetChannel(name string) (Channel, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	channel, ok := m.channels[name]
	return channel, ok
}

func (m *Manager) HasChannel(name string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	_, ok := m.channels[name]
	return ok
}

func (m *Manager) GetStatus() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	status := make(map[string]interface{})
	for name, channel := range m.channels {
		status[name] = map[string]interface{}{
			"enabled": true,
			"running": channel.IsRunning(),
		}
	}
	return status
}

func (m *Manager) GetEnabledChannels() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	names := make([]string, 0, len(m.channels))
	for name := range m.channels {
		names = append(names, name)
	}
	return names
}

func (m *Manager) RegisterChannel(name string, channel Channel) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.channels[name] = channel
}

func (m *Manager) UnregisterChannel(name string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.channels, name)
}

func (m *Manager) SendToChannel(ctx context.Context, channelName, chatID, content string) error {
	m.mu.RLock()
	channel, exists := m.channels[channelName]
	m.mu.RUnlock()

	if !exists {
		return fmt.Errorf("channel %s not found", channelName)
	}

	msg := bus.OutboundMessage{
		Channel: channelName,
		ChatID:  chatID,
		Content: content,
	}

	return channel.Send(ctx, msg)
}
