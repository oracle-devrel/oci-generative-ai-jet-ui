package main

import (
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"agent-reasoning-tui/internal/app"
	"agent-reasoning-tui/internal/config"
	"agent-reasoning-tui/internal/server"
	"agent-reasoning-tui/internal/views"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	// Find project directory (parent of tui/)
	execPath, err := os.Executable()
	if err != nil {
		execPath, _ = os.Getwd()
	}

	// Try to find project root by looking for server.py
	projectDir := findProjectRoot(execPath)
	if projectDir == "" {
		// Fallback: assume we're in the tui directory
		cwd, _ := os.Getwd()
		projectDir = filepath.Dir(cwd)
		if _, err := os.Stat(filepath.Join(projectDir, "server.py")); os.IsNotExist(err) {
			// Try current directory's parent
			projectDir = filepath.Dir(filepath.Dir(cwd))
		}
	}

	// Verify server.py exists
	serverPath := filepath.Join(projectDir, "server.py")
	if _, err := os.Stat(serverPath); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: server.py not found. Please run from the project directory.\n")
		fmt.Fprintf(os.Stderr, "Looked in: %s\n", projectDir)
		os.Exit(1)
	}

	fmt.Println("Starting Agent Reasoning TUI...")
	fmt.Printf("Project directory: %s\n", projectDir)

	// Load config
	configPath := filepath.Join(os.Getenv("HOME"), ".config", "agent-reasoning", "config.yaml")
	cfg := config.Load(configPath)

	// Create server manager
	serverMgr := server.NewManager(projectDir)

	// Start the server
	fmt.Println("Starting reasoning server...")
	if err := serverMgr.Start(); err != nil {
		fmt.Fprintf(os.Stderr, "Error starting server: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("Server started successfully!")

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-sigChan
		fmt.Println("\nShutting down...")
		serverMgr.Stop()
		os.Exit(0)
	}()

	// Create the root model with config
	model := app.NewWithConfig(cfg, projectDir)

	// Create and register views
	chatView := views.NewChatView(model.Ctx())
	model.Router().RegisterView(chatView)

	arenaView := views.NewArenaView(model.Ctx())
	model.Router().RegisterView(arenaView)

	duelView := views.NewDuelView(model.Ctx())
	model.Router().RegisterView(duelView)

	benchmarkView := views.NewBenchmarkView(model.Ctx())
	model.Router().RegisterView(benchmarkView)

	agentInfoView := views.NewAgentInfoView(model.Ctx())
	model.Router().RegisterView(agentInfoView)

	debugView := views.NewDebugView(model.Ctx())
	model.Router().RegisterView(debugView)

	sessionsView := views.NewSessionsView(model.Ctx())
	model.Router().RegisterView(sessionsView)

	p := tea.NewProgram(model, tea.WithAltScreen())

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running TUI: %v\n", err)
		serverMgr.Stop()
		os.Exit(1)
	}

	// Clean shutdown
	fmt.Println("Stopping server...")
	serverMgr.Stop()
	fmt.Println("Goodbye!")
}

// findProjectRoot looks for the project root by searching for server.py
func findProjectRoot(startPath string) string {
	// Start from the directory containing the executable
	dir := filepath.Dir(startPath)

	// Walk up the directory tree
	for i := 0; i < 5; i++ {
		serverPath := filepath.Join(dir, "server.py")
		if _, err := os.Stat(serverPath); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}

	// Also check current working directory
	cwd, err := os.Getwd()
	if err == nil {
		serverPath := filepath.Join(cwd, "server.py")
		if _, err := os.Stat(serverPath); err == nil {
			return cwd
		}
		// Check parent of cwd (in case we're in tui/)
		parent := filepath.Dir(cwd)
		serverPath = filepath.Join(parent, "server.py")
		if _, err := os.Stat(serverPath); err == nil {
			return parent
		}
	}

	return ""
}
