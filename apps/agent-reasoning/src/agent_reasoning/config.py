"""Configuration management for Agent Reasoning."""

from pathlib import Path

import yaml

# Default configuration
DEFAULT_CONFIG = {"ollama": {"host": "http://localhost:11434"}}

# Config directory and file path
# Config directory and file path
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return CONFIG_DIR


def get_config_file() -> Path:
    """Get the configuration file path."""
    return CONFIG_FILE


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    # Config is in repo root, so directory should always exist
    pass


def load_config() -> dict:
    """
    Load configuration from the YAML file.

    Returns default config if file doesn't exist.
    Merges with defaults to ensure all keys are present.
    """
    import copy

    config = copy.deepcopy(DEFAULT_CONFIG)

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = yaml.safe_load(f) or {}

            # Deep merge user config with defaults
            for key, value in user_config.items():
                if isinstance(value, dict) and key in config:
                    config[key].update(value)
                else:
                    config[key] = value
        except Exception:
            # If config is corrupted, use defaults
            pass

    return config


def save_config(config: dict) -> None:
    """Save configuration to the YAML file."""
    ensure_config_dir()

    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)


def get_ollama_host() -> str:
    """Get the Ollama host URL from config."""
    config = load_config()
    return config.get("ollama", {}).get("host", DEFAULT_CONFIG["ollama"]["host"])


def set_ollama_host(host: str) -> None:
    """Set the Ollama host URL in config."""
    config = load_config()
    if "ollama" not in config:
        config["ollama"] = {}
    config["ollama"]["host"] = host
    save_config(config)
