package routing

import (
	"github.com/jasperan/picooraclaw/pkg/providers"
)

const defaultThreshold = 0.35

// DefaultAgentID is the agent ID used when no explicit agent is configured.
const DefaultAgentID = "main"

// NormalizeAgentID normalizes an agent ID to lowercase with hyphens replacing spaces.
func NormalizeAgentID(id string) string {
	if id == "" {
		return DefaultAgentID
	}
	return id
}

type RouterConfig struct {
	LightModel string
	Threshold  float64
}

// Router selects the appropriate model tier for each incoming message.
type Router struct {
	cfg        RouterConfig
	classifier Classifier
}

func New(cfg RouterConfig) *Router {
	if cfg.Threshold <= 0 {
		cfg.Threshold = defaultThreshold
	}
	return &Router{
		cfg:        cfg,
		classifier: &RuleClassifier{},
	}
}

// SelectModel returns the model to use for this conversation turn.
func (r *Router) SelectModel(
	msg string,
	history []providers.Message,
	primaryModel string,
) (model string, usedLight bool, score float64) {
	features := ExtractFeatures(msg, history)
	score = r.classifier.Score(features)
	if score < r.cfg.Threshold {
		return r.cfg.LightModel, true, score
	}
	return primaryModel, false, score
}

func (r *Router) LightModel() string {
	return r.cfg.LightModel
}

func (r *Router) Threshold() float64 {
	return r.cfg.Threshold
}
