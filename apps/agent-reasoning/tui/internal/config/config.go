package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type ServerConfig struct {
	Port         int    `yaml:"port"`
	AutoStart    bool   `yaml:"auto_start"`
	StartTimeout string `yaml:"start_timeout"`
}

type OllamaConfig struct {
	URL string `yaml:"url"`
}

type DefaultsConfig struct {
	Model         string `yaml:"model"`
	Visualization bool   `yaml:"visualization"`
}

type UIConfig struct {
	SidebarWidth int    `yaml:"sidebar_width"`
	ColorTheme   string `yaml:"color_theme"`
	MetricsBar   bool   `yaml:"metrics_bar"`
}

type SessionsConfig struct {
	AutoSave  bool   `yaml:"auto_save"`
	Directory string `yaml:"directory"`
}

type Config struct {
	Server   ServerConfig   `yaml:"server"`
	Ollama   OllamaConfig   `yaml:"ollama"`
	Defaults DefaultsConfig `yaml:"defaults"`
	UI       UIConfig       `yaml:"ui"`
	Sessions SessionsConfig `yaml:"sessions"`
}

func DefaultConfig() Config {
	return Config{
		Server: ServerConfig{
			Port:         8080,
			AutoStart:    true,
			StartTimeout: "10s",
		},
		Ollama: OllamaConfig{
			URL: "http://localhost:11434",
		},
		Defaults: DefaultsConfig{
			Model:         "gemma3:latest",
			Visualization: true,
		},
		UI: UIConfig{
			SidebarWidth: 22,
			ColorTheme:   "default",
			MetricsBar:   true,
		},
		Sessions: SessionsConfig{
			AutoSave:  true,
			Directory: "data/sessions",
		},
	}
}

func Load(path string) Config {
	cfg := DefaultConfig()
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg
	}
	yaml.Unmarshal(data, &cfg)
	return cfg
}
