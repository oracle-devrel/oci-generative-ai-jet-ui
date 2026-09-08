package routing

// Classifier evaluates a feature set and returns a complexity score in [0, 1].
type Classifier interface {
	Score(f Features) float64
}

// RuleClassifier is a weighted-sum implementation with sub-microsecond latency.
type RuleClassifier struct{}

// Score computes the complexity score for the given feature set.
func (c *RuleClassifier) Score(f Features) float64 {
	if f.HasAttachments {
		return 1.0
	}

	var score float64

	switch {
	case f.TokenEstimate > 200:
		score += 0.35
	case f.TokenEstimate > 50:
		score += 0.15
	}

	if f.CodeBlockCount > 0 {
		score += 0.40
	}

	switch {
	case f.RecentToolCalls > 3:
		score += 0.25
	case f.RecentToolCalls > 0:
		score += 0.10
	}

	if f.ConversationDepth > 10 {
		score += 0.10
	}

	if score > 1.0 {
		score = 1.0
	}
	return score
}
