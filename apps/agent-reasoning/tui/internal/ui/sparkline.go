package ui

import "github.com/charmbracelet/lipgloss"

var sparkChars = []rune{'▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'}

var sparkStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#00FFFF"))

// Sparkline renders inline charts using block characters.
type Sparkline struct {
	values []float64
	width  int
}

func NewSparkline(width int) *Sparkline {
	return &Sparkline{width: width}
}

// Push adds a value and trims history to width.
func (s *Sparkline) Push(value float64) {
	s.values = append(s.values, value)
	if len(s.values) > s.width {
		s.values = s.values[len(s.values)-s.width:]
	}
}

// View renders using sparkChars assuming values are in [0,1] range.
func (s *Sparkline) View() string {
	if len(s.values) == 0 {
		return sparkStyle.Render(padRight("", s.width))
	}
	runes := make([]rune, s.width)
	for i := range runes {
		runes[i] = ' '
	}
	offset := s.width - len(s.values)
	if offset < 0 {
		offset = 0
	}
	src := s.values
	if len(src) > s.width {
		src = src[len(src)-s.width:]
	}
	for i, v := range src {
		idx := int(v * float64(len(sparkChars)-1))
		if idx < 0 {
			idx = 0
		}
		if idx >= len(sparkChars) {
			idx = len(sparkChars) - 1
		}
		runes[offset+i] = sparkChars[idx]
	}
	return sparkStyle.Render(string(runes))
}

// NormalizedView auto-scales to the min/max of the current data.
func (s *Sparkline) NormalizedView() string {
	if len(s.values) == 0 {
		return sparkStyle.Render(padRight("", s.width))
	}
	min, max := s.values[0], s.values[0]
	for _, v := range s.values {
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}
	rng := max - min
	normalized := make([]float64, len(s.values))
	for i, v := range s.values {
		if rng == 0 {
			normalized[i] = 0.5
		} else {
			normalized[i] = (v - min) / rng
		}
	}
	tmp := &Sparkline{values: normalized, width: s.width}
	return tmp.View()
}

func padRight(s string, width int) string {
	for len([]rune(s)) < width {
		s += " "
	}
	return s
}
