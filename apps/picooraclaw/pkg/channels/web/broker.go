package web

import (
	"sync"
	"time"
)

type Event struct {
	Type       string         `json:"type"`
	SessionID  string         `json:"session_id,omitempty"`
	MessageID  string         `json:"message_id,omitempty"`
	ToolCallID string         `json:"id,omitempty"`
	Tool       string         `json:"tool,omitempty"`
	Args       map[string]any `json:"args,omitempty"`
	Result     string         `json:"result,omitempty"`
	OK         *bool          `json:"ok,omitempty"`
	Text       string         `json:"text,omitempty"`
	Error      string         `json:"error,omitempty"`
	Note       string         `json:"note,omitempty"`
	Timestamp  time.Time      `json:"ts"`
}

const (
	bufferPerSession = 1000
	subChanSize      = 64
)

type Subscription struct {
	C         chan Event
	sessionID string
	id        uint64
}

type EventBroker struct {
	mu      sync.RWMutex
	buffers map[string][]Event
	subs    map[string]map[uint64]*Subscription
	nextID  uint64
}

func NewEventBroker() *EventBroker {
	return &EventBroker{
		buffers: make(map[string][]Event),
		subs:    make(map[string]map[uint64]*Subscription),
	}
}

func (b *EventBroker) Emit(e Event) {
	// Step 1: buffer update under WLock
	b.mu.Lock()
	buf := b.buffers[e.SessionID]
	buf = append(buf, e)
	if len(buf) > bufferPerSession {
		buf = buf[len(buf)-bufferPerSession:]
	}
	b.buffers[e.SessionID] = buf
	b.mu.Unlock()

	// Step 2: fan-out under RLock — serialises with Unsubscribe's WLock so we
	// never send on a closed channel. Unsubscribe removes the sub from the map
	// and closes the channel under WLock; by holding RLock here we are
	// guaranteed to either see the sub (safe to send) or not see it (already
	// removed before close).
	b.mu.RLock()
	defer b.mu.RUnlock()
	for _, s := range b.subs[e.SessionID] {
		select {
		case s.C <- e:
		default:
			// Drop if consumer is slow; they can resume via cursor on reconnect.
		}
	}
}

func (b *EventBroker) Subscribe(sessionID, fromMessageID string) *Subscription {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.nextID++
	sub := &Subscription{C: make(chan Event, subChanSize), sessionID: sessionID, id: b.nextID}

	if _, ok := b.subs[sessionID]; !ok {
		b.subs[sessionID] = make(map[uint64]*Subscription)
	}
	b.subs[sessionID][sub.id] = sub

	if fromMessageID != "" {
		buf := b.buffers[sessionID]
		startIdx := -1
		for i, e := range buf {
			if e.MessageID == fromMessageID {
				startIdx = i
			}
		}
		if startIdx >= 0 {
			for _, e := range buf[startIdx+1:] {
				select {
				case sub.C <- e:
				default:
				}
			}
		}
	}
	return sub
}

func (b *EventBroker) Unsubscribe(sub *Subscription) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if m, ok := b.subs[sub.sessionID]; ok {
		delete(m, sub.id)
	}
	close(sub.C)
}
