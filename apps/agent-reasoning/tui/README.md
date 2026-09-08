# Agent Reasoning TUI

A terminal user interface for the Agent Reasoning system, built with [Bubble Tea](https://github.com/charmbracelet/bubbletea) and [Lipgloss](https://github.com/charmbracelet/lipgloss).

## Building

```bash
cd tui
go build -o agent-tui .
```

## Running

```bash
# From the tui directory
./agent-tui

# Or from the project root
./tui/agent-tui
```

The TUI will automatically start `server.py` when launched and stop it when you exit.

## Prerequisites

- Go 1.18+
- Python 3.10+ (for server.py)
- Ollama running locally (http://localhost:11434)

## Keybindings

| Key | Action |
|-----|--------|
| `↑/↓` or `j/k` | Navigate sidebar |
| `Enter` | Select agent / submit query |
| `Tab` | Toggle focus (sidebar ↔ input) |
| `Esc` | Cancel streaming / exit arena |
| `q` or `Ctrl+C` | Quit |

## Features

- **9 Reasoning Agents**: Standard, CoT, ToT, ReAct, Recursive, Reflection, Decomposed, Least-to-Most, Consistency
- **Arena Mode**: Run all agents on the same query in a 3x3 grid view
- **Model Selection**: Fetch available models from Ollama
- **Streaming**: Real-time response streaming with cancellation support
- **Auto Server Management**: Automatically starts/stops the Python backend
