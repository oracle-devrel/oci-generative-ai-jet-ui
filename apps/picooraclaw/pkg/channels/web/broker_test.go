package web

import (
	"testing"
	"time"
)

func TestEventBroker_SubscribeAndFanOut(t *testing.T) {
	b := NewEventBroker()

	subA := b.Subscribe("s1", "")
	subB := b.Subscribe("s1", "")
	subOther := b.Subscribe("s2", "")
	defer b.Unsubscribe(subA)
	defer b.Unsubscribe(subB)
	defer b.Unsubscribe(subOther)

	e := Event{Type: "message_start", SessionID: "s1", MessageID: "m1", Timestamp: time.Now()}
	b.Emit(e)

	if got := recv(t, subA.C); got.MessageID != "m1" {
		t.Fatalf("subA missed event: %+v", got)
	}
	if got := recv(t, subB.C); got.MessageID != "m1" {
		t.Fatalf("subB missed event: %+v", got)
	}
	select {
	case got := <-subOther.C:
		t.Fatalf("subOther should not receive session s1 event, got %+v", got)
	case <-time.After(50 * time.Millisecond):
		// ok
	}
}

func TestEventBroker_ResumeFromCursor(t *testing.T) {
	b := NewEventBroker()
	b.Emit(Event{Type: "a", SessionID: "s1", MessageID: "m1"})
	b.Emit(Event{Type: "b", SessionID: "s1", MessageID: "m2"})

	sub := b.Subscribe("s1", "m1")
	defer b.Unsubscribe(sub)

	got := recv(t, sub.C)
	if got.MessageID != "m2" {
		t.Fatalf("expected m2, got %+v", got)
	}
}

func TestEventBroker_NoSendOnClosed(t *testing.T) {
	b := NewEventBroker()
	const N = 20
	subs := make([]*Subscription, N)
	for i := range subs {
		subs[i] = b.Subscribe("s1", "")
	}
	done := make(chan struct{})
	go func() {
		defer close(done)
		for i := 0; i < 100; i++ {
			b.Emit(Event{Type: "t", SessionID: "s1", MessageID: "m"})
		}
	}()
	// Unsubscribe half concurrently
	for i := 0; i < N/2; i++ {
		b.Unsubscribe(subs[i])
	}
	<-done
	// If we reach here without panicking, the fix works.
	for i := N / 2; i < N; i++ {
		b.Unsubscribe(subs[i])
	}
}

func recv(t *testing.T, c <-chan Event) Event {
	t.Helper()
	select {
	case e := <-c:
		return e
	case <-time.After(250 * time.Millisecond):
		t.Fatal("timeout waiting for event")
	}
	return Event{}
}
