package app

import (
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

// mockView implements the View interface for testing
type mockView struct {
	id        ViewID
	initCalls int
	updates   int
	width     int
	height    int
	viewText  string
}

func (v *mockView) Init() tea.Cmd                          { v.initCalls++; return nil }
func (v *mockView) Update(msg tea.Msg) (View, tea.Cmd)    { v.updates++; return v, nil }
func (v *mockView) View() string                          { return v.viewText }
func (v *mockView) SetSize(w, h int)                      { v.width = w; v.height = h }
func (v *mockView) ID() ViewID                            { return v.id }

func TestNewRouter(t *testing.T) {
	chat := &mockView{id: ViewChat, viewText: "chat"}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)

	if r.ActiveID() != ViewChat {
		t.Error("expected initial view to be chat")
	}
	if r.ActiveView() == nil {
		t.Error("expected non-nil active view")
	}
}

func TestRouterSwitchView(t *testing.T) {
	chat := &mockView{id: ViewChat, viewText: "chat"}
	arena := &mockView{id: ViewArena, viewText: "arena"}

	r := NewRouter(map[ViewID]View{
		ViewChat:  chat,
		ViewArena: arena,
	}, ViewChat)

	r.SwitchTo(ViewArena)
	if r.ActiveID() != ViewArena {
		t.Error("expected arena after switch")
	}
	if arena.initCalls != 1 {
		t.Errorf("expected Init called once on arena, got %d", arena.initCalls)
	}
}

func TestRouterSwitchToNonexistent(t *testing.T) {
	chat := &mockView{id: ViewChat}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)

	cmd := r.SwitchTo(ViewDebug) // not registered
	if cmd != nil {
		t.Error("expected nil cmd for nonexistent view")
	}
	if r.ActiveID() != ViewChat {
		t.Error("should stay on chat")
	}
}

func TestRouterSetSizePropagates(t *testing.T) {
	chat := &mockView{id: ViewChat}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)
	r.SetSize(120, 40)
	if chat.width != 120 || chat.height != 40 {
		t.Errorf("expected 120x40, got %dx%d", chat.width, chat.height)
	}
}

func TestRouterUpdate(t *testing.T) {
	chat := &mockView{id: ViewChat}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)
	r.Update(tea.KeyMsg{})
	if chat.updates != 1 {
		t.Errorf("expected 1 update, got %d", chat.updates)
	}
}

func TestRouterView(t *testing.T) {
	chat := &mockView{id: ViewChat, viewText: "hello"}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)
	if r.View() != "hello" {
		t.Errorf("expected 'hello', got '%s'", r.View())
	}
}

func TestRouterRegisterView(t *testing.T) {
	chat := &mockView{id: ViewChat}
	r := NewRouter(map[ViewID]View{ViewChat: chat}, ViewChat)

	arena := &mockView{id: ViewArena, viewText: "arena"}
	r.RegisterView(arena)

	r.SwitchTo(ViewArena)
	if r.View() != "arena" {
		t.Error("expected arena view after registering and switching")
	}
}
