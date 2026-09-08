package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Server.Port != 8080 {
		t.Errorf("expected port 8080, got %d", cfg.Server.Port)
	}
	if cfg.Defaults.Model != "gemma3:latest" {
		t.Errorf("expected gemma3:latest, got %s", cfg.Defaults.Model)
	}
	if !cfg.Sessions.AutoSave {
		t.Error("expected auto_save true by default")
	}
	if !cfg.Defaults.Visualization {
		t.Error("expected visualization true by default")
	}
	if cfg.UI.SidebarWidth != 22 {
		t.Errorf("expected sidebar width 22, got %d", cfg.UI.SidebarWidth)
	}
}

func TestLoadConfigMissing(t *testing.T) {
	cfg := Load("/nonexistent/path/config.yaml")
	if cfg.Server.Port != 8080 {
		t.Error("missing config should return defaults")
	}
}

func TestLoadConfigFromFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	os.WriteFile(path, []byte("server:\n  port: 9090\ndefaults:\n  model: llama3:8b\n"), 0644)

	cfg := Load(path)
	if cfg.Server.Port != 9090 {
		t.Errorf("expected 9090, got %d", cfg.Server.Port)
	}
	if cfg.Defaults.Model != "llama3:8b" {
		t.Errorf("expected llama3:8b, got %s", cfg.Defaults.Model)
	}
	// Unset fields should still have defaults
	if !cfg.Sessions.AutoSave {
		t.Error("unset auto_save should default to true")
	}
	if cfg.Ollama.URL != "http://localhost:11434" {
		t.Error("unset ollama URL should keep default")
	}
}

func TestLoadConfigPartialOverride(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.yaml")
	os.WriteFile(path, []byte("ui:\n  sidebar_width: 30\n  metrics_bar: false\n"), 0644)

	cfg := Load(path)
	if cfg.UI.SidebarWidth != 30 {
		t.Errorf("expected 30, got %d", cfg.UI.SidebarWidth)
	}
	if cfg.UI.MetricsBar {
		t.Error("expected metrics_bar false")
	}
	// Other UI fields should keep defaults
	if cfg.UI.ColorTheme != "default" {
		t.Error("unset color_theme should keep default")
	}
}
