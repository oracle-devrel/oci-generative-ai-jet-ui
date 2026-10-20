package sample

import "fmt"

// Greet returns a greeting. Line numbers are asserted in test_chunker.py.
func Greet(name string) string {
	return fmt.Sprintf("hello %s", name)
}

type Counter struct {
	n int
}

func (c *Counter) Bump() int {
	c.n++
	return c.n
}

type Greeter interface {
	Greet(name string) string
}

type (
	Point struct {
		X, Y int
	}
	Shape interface {
		Area() float64
	}
)

type Engine[T any] struct {
	items []T
}

func (e *Engine[T]) Use(item T) {
	e.items = append(e.items, item)
}
