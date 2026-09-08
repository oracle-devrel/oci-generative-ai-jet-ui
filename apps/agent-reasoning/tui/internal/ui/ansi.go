package ui

// ansiStrip removes ANSI escape sequences from s.
func ansiStrip(s string) string {
	result := make([]rune, 0, len(s))
	inEsc := false
	for _, r := range s {
		if r == '\x1b' {
			inEsc = true
			continue
		}
		if inEsc {
			if r == 'm' {
				inEsc = false
			}
			continue
		}
		result = append(result, r)
	}
	return string(result)
}
