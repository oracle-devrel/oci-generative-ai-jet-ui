// PicoOraClaw - Ultra-lightweight personal AI agent with Oracle AI Database
// Based on PicoClaw, inspired by nanobot: https://github.com/HKUDS/nanobot
// License: MIT
//
// Copyright (c) 2026 PicoOraClaw contributors

package main

import (
	"bufio"
	"context"
	"database/sql"
	"embed"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/chzyer/readline"
	"github.com/jasperan/picooraclaw/pkg/agent"
	"github.com/jasperan/picooraclaw/pkg/auth"
	"github.com/jasperan/picooraclaw/pkg/bus"
	"github.com/jasperan/picooraclaw/pkg/channels"
	"github.com/jasperan/picooraclaw/pkg/channels/web"
	"github.com/jasperan/picooraclaw/pkg/config"
	"github.com/jasperan/picooraclaw/pkg/cron"
	"github.com/jasperan/picooraclaw/pkg/devices"
	"github.com/jasperan/picooraclaw/pkg/health"
	"github.com/jasperan/picooraclaw/pkg/heartbeat"
	"github.com/jasperan/picooraclaw/pkg/logger"
	"github.com/jasperan/picooraclaw/pkg/migrate"
	oracledb "github.com/jasperan/picooraclaw/pkg/oracle"
	"github.com/jasperan/picooraclaw/pkg/providers"
	"github.com/jasperan/picooraclaw/pkg/skills"
	"github.com/jasperan/picooraclaw/pkg/state"
	"github.com/jasperan/picooraclaw/pkg/tools"
	"github.com/jasperan/picooraclaw/pkg/voice"
)

//go:generate cp -r ../../workspace .
//go:embed workspace
var embeddedFiles embed.FS

var (
	version   = "dev"
	gitCommit string
	buildTime string
	goVersion string
)

const logo = "🦞"

// formatVersion returns the version string with optional git commit
func formatVersion() string {
	v := version
	if gitCommit != "" {
		v += fmt.Sprintf(" (git: %s)", gitCommit)
	}
	return v
}

// formatBuildInfo returns build time and go version info
func formatBuildInfo() (build string, goVer string) {
	if buildTime != "" {
		build = buildTime
	}
	goVer = goVersion
	if goVer == "" {
		goVer = runtime.Version()
	}
	return
}

func printVersion() {
	fmt.Printf("%s picooraclaw %s\n", logo, formatVersion())
	build, goVer := formatBuildInfo()
	if build != "" {
		fmt.Printf("  Build: %s\n", build)
	}
	if goVer != "" {
		fmt.Printf("  Go: %s\n", goVer)
	}
}

func main() {
	if len(os.Args) < 2 {
		printHelp()
		os.Exit(1)
	}

	command := os.Args[1]

	switch command {
	case "onboard":
		onboard()
	case "agent":
		agentCmd()
	case "gateway":
		gatewayCmd()
	case "status":
		statusCmd()
	case "migrate":
		migrateCmd()
	case "auth":
		authCmd()
	case "cron":
		cronCmd()
	case "setup-oracle":
		setupOracleCmd()
	case "oracle-inspect":
		oracleInspectCmd()
	case "seed-demo":
		seedDemoCmd()
	case "skills":
		if len(os.Args) < 3 {
			skillsHelp()
			return
		}

		subcommand := os.Args[2]

		cfg, err := loadConfig()
		if err != nil {
			fmt.Printf("Error loading config: %v\n", err)
			os.Exit(1)
		}

		workspace := cfg.WorkspacePath()
		installer := skills.NewSkillInstaller(workspace)
		// 获取全局配置目录和内置 skills 目录
		globalDir := filepath.Dir(getConfigPath())
		globalSkillsDir := filepath.Join(globalDir, "skills")
		builtinSkillsDir := filepath.Join(globalDir, "picoclaw", "skills")
		skillsLoader := skills.NewSkillsLoader(workspace, globalSkillsDir, builtinSkillsDir)

		switch subcommand {
		case "list":
			skillsListCmd(skillsLoader)
		case "install":
			skillsInstallCmd(installer)
		case "remove", "uninstall":
			if len(os.Args) < 4 {
				fmt.Println("Usage: picooraclaw skills remove <skill-name>")
				return
			}
			skillsRemoveCmd(installer, os.Args[3])
		case "install-builtin":
			skillsInstallBuiltinCmd(workspace)
		case "list-builtin":
			skillsListBuiltinCmd()
		case "search":
			skillsSearchCmd(installer)
		case "show":
			if len(os.Args) < 4 {
				fmt.Println("Usage: picooraclaw skills show <skill-name>")
				return
			}
			skillsShowCmd(skillsLoader, os.Args[3])
		default:
			fmt.Printf("Unknown skills command: %s\n", subcommand)
			skillsHelp()
		}
	case "version", "--version", "-v":
		printVersion()
	default:
		fmt.Printf("Unknown command: %s\n", command)
		printHelp()
		os.Exit(1)
	}
}

func printHelp() {
	fmt.Printf("%s picooraclaw - Personal AI Assistant with Oracle AI Database v%s\n\n", logo, version)
	fmt.Println("Usage: picooraclaw <command>")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  onboard        Initialize picooraclaw configuration and workspace")
	fmt.Println("  agent          Interact with the agent directly")
	fmt.Println("  auth           Manage authentication (login, logout, status)")
	fmt.Println("  gateway        Start picooraclaw gateway")
	fmt.Println("  status         Show picooraclaw status")
	fmt.Println("  cron           Manage scheduled tasks")
	fmt.Println("  migrate        Migrate from OpenClaw/PicoClaw")
	fmt.Println("  skills         Manage skills (install, list, remove)")
	fmt.Println("  setup-oracle   Initialize Oracle Database schema and ONNX model")
	fmt.Println("  oracle-inspect Inspect data stored in Oracle Database")
	fmt.Println("  seed-demo      Populate Oracle with realistic demo data")
	fmt.Println("  version        Show version information")
}

func onboard() {
	configPath := getConfigPath()

	if _, err := os.Stat(configPath); err == nil {
		fmt.Printf("Config already exists at %s\n", configPath)
		fmt.Print("Overwrite? (y/n): ")
		var response string
		fmt.Scanln(&response)
		if response != "y" {
			fmt.Println("Aborted.")
			return
		}
	}

	cfg := config.DefaultConfig()
	if err := config.SaveConfig(configPath, cfg); err != nil {
		fmt.Printf("Error saving config: %v\n", err)
		os.Exit(1)
	}

	workspace := cfg.WorkspacePath()
	createWorkspaceTemplates(workspace)

	fmt.Printf("%s picooraclaw is ready!\n", logo)
	fmt.Println("\nNext steps:")
	fmt.Println("  1. Add your API key to", configPath)
	fmt.Println("     Get one at: https://openrouter.ai/keys")
	fmt.Println("  2. Chat: picooraclaw agent -m \"Hello!\"")
}

func copyEmbeddedToTarget(targetDir string) error {
	// Ensure target directory exists
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return fmt.Errorf("Failed to create target directory: %w", err)
	}

	// Walk through all files in embed.FS
	err := fs.WalkDir(embeddedFiles, "workspace", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if d.IsDir() {
			return nil
		}

		// Read embedded file
		data, err := embeddedFiles.ReadFile(path)
		if err != nil {
			return fmt.Errorf("Failed to read embedded file %s: %w", path, err)
		}

		new_path, err := filepath.Rel("workspace", path)
		if err != nil {
			return fmt.Errorf("Failed to get relative path for %s: %v\n", path, err)
		}

		// Build target file path
		targetPath := filepath.Join(targetDir, new_path)

		// Ensure target file's directory exists
		if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
			return fmt.Errorf("Failed to create directory %s: %w", filepath.Dir(targetPath), err)
		}

		// Write file
		if err := os.WriteFile(targetPath, data, 0644); err != nil {
			return fmt.Errorf("Failed to write file %s: %w", targetPath, err)
		}

		return nil
	})

	return err
}

func createWorkspaceTemplates(workspace string) {
	err := copyEmbeddedToTarget(workspace)
	if err != nil {
		fmt.Printf("Error copying workspace templates: %v\n", err)
	}
}

func migrateCmd() {
	if len(os.Args) > 2 && (os.Args[2] == "--help" || os.Args[2] == "-h") {
		migrateHelp()
		return
	}

	opts := migrate.Options{}

	args := os.Args[2:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--dry-run":
			opts.DryRun = true
		case "--config-only":
			opts.ConfigOnly = true
		case "--workspace-only":
			opts.WorkspaceOnly = true
		case "--force":
			opts.Force = true
		case "--refresh":
			opts.Refresh = true
		case "--openclaw-home":
			if i+1 < len(args) {
				opts.OpenClawHome = args[i+1]
				i++
			}
		case "--picoclaw-home":
			if i+1 < len(args) {
				opts.PicoClawHome = args[i+1]
				i++
			}
		default:
			fmt.Printf("Unknown flag: %s\n", args[i])
			migrateHelp()
			os.Exit(1)
		}
	}

	result, err := migrate.Run(opts)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}

	if !opts.DryRun {
		migrate.PrintSummary(result)
	}
}

func migrateHelp() {
	fmt.Println("\nMigrate from OpenClaw/PicoClaw to PicoOraClaw")
	fmt.Println()
	fmt.Println("Usage: picooraclaw migrate [options]")
	fmt.Println()
	fmt.Println("Options:")
	fmt.Println("  --dry-run          Show what would be migrated without making changes")
	fmt.Println("  --refresh          Re-sync workspace files (repeatable)")
	fmt.Println("  --config-only      Only migrate config, skip workspace files")
	fmt.Println("  --workspace-only   Only migrate workspace files, skip config")
	fmt.Println("  --force            Skip confirmation prompts")
	fmt.Println("  --openclaw-home    Override OpenClaw home directory (default: ~/.openclaw)")
	fmt.Println("  --picoclaw-home    Override PicoOraClaw home directory (default: ~/.picooraclaw)")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  picooraclaw migrate              Detect and migrate from OpenClaw")
	fmt.Println("  picooraclaw migrate --dry-run    Show what would be migrated")
	fmt.Println("  picooraclaw migrate --refresh    Re-sync workspace files")
	fmt.Println("  picooraclaw migrate --force      Migrate without confirmation")
}

func agentCmd() {
	message := ""
	sessionKey := "cli:default"

	args := os.Args[2:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--debug", "-d":
			logger.SetLevel(logger.DEBUG)
			fmt.Println("🔍 Debug mode enabled")
		case "-m", "--message":
			if i+1 < len(args) {
				message = args[i+1]
				i++
			}
		case "-s", "--session":
			if i+1 < len(args) {
				sessionKey = args[i+1]
				i++
			}
		}
	}

	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		os.Exit(1)
	}

	provider, err := providers.CreateProvider(cfg)
	if err != nil {
		fmt.Printf("Error creating provider: %v\n", err)
		os.Exit(1)
	}

	msgBus := bus.NewMessageBus()

	var agentLoop *agent.AgentLoop
	var oracleConn *oracledb.ConnectionManager

	if cfg.Oracle.Enabled {
		agentLoop, oracleConn, _, err = initOracleAgent(cfg, msgBus, provider)
		if err != nil {
			fmt.Printf("Oracle initialization failed: %v\n", err)
			fmt.Println("Falling back to file-based storage...")
			agentLoop = agent.NewAgentLoop(cfg, msgBus, provider)
		} else {
			defer oracleConn.Close()
			fmt.Println("✓ Oracle AI Database storage enabled")
		}
	} else {
		agentLoop = agent.NewAgentLoop(cfg, msgBus, provider)
	}

	// Print agent startup info (only for interactive mode)
	startupInfo := agentLoop.GetStartupInfo()
	logger.InfoCF("agent", "Agent initialized",
		map[string]interface{}{
			"tools_count":      startupInfo["tools"].(map[string]interface{})["count"],
			"skills_total":     startupInfo["skills"].(map[string]interface{})["total"],
			"skills_available": startupInfo["skills"].(map[string]interface{})["available"],
		})

	if message != "" {
		ctx := context.Background()
		response, err := agentLoop.ProcessDirect(ctx, message, sessionKey)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("\n%s %s\n", logo, response)
	} else {
		fmt.Printf("%s Interactive mode (Ctrl+C to exit)\n\n", logo)
		interactiveMode(agentLoop, sessionKey)
	}
}

func interactiveMode(agentLoop *agent.AgentLoop, sessionKey string) {
	prompt := fmt.Sprintf("%s You: ", logo)

	rl, err := readline.NewEx(&readline.Config{
		Prompt:          prompt,
		HistoryFile:     filepath.Join(os.TempDir(), ".picooraclaw_history"),
		HistoryLimit:    100,
		InterruptPrompt: "^C",
		EOFPrompt:       "exit",
	})

	if err != nil {
		fmt.Printf("Error initializing readline: %v\n", err)
		fmt.Println("Falling back to simple input mode...")
		simpleInteractiveMode(agentLoop, sessionKey)
		return
	}
	defer rl.Close()

	for {
		line, err := rl.Readline()
		if err != nil {
			if err == readline.ErrInterrupt || err == io.EOF {
				fmt.Println("\nGoodbye!")
				return
			}
			fmt.Printf("Error reading input: %v\n", err)
			continue
		}

		input := strings.TrimSpace(line)
		if input == "" {
			continue
		}

		if input == "exit" || input == "quit" {
			fmt.Println("Goodbye!")
			return
		}

		ctx := context.Background()
		response, err := agentLoop.ProcessDirect(ctx, input, sessionKey)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}

		fmt.Printf("\n%s %s\n\n", logo, response)
	}
}

func simpleInteractiveMode(agentLoop *agent.AgentLoop, sessionKey string) {
	reader := bufio.NewReader(os.Stdin)
	for {
		fmt.Printf("%s You: ", logo)
		line, err := reader.ReadString('\n')
		if err != nil {
			if err == io.EOF {
				fmt.Println("\nGoodbye!")
				return
			}
			fmt.Printf("Error reading input: %v\n", err)
			continue
		}

		input := strings.TrimSpace(line)
		if input == "" {
			continue
		}

		if input == "exit" || input == "quit" {
			fmt.Println("Goodbye!")
			return
		}

		ctx := context.Background()
		response, err := agentLoop.ProcessDirect(ctx, input, sessionKey)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}

		fmt.Printf("\n%s %s\n\n", logo, response)
	}
}

func gatewayCmd() {
	// Check for --debug and --enable-web flags
	args := os.Args[2:]
	enableWeb := false
	for _, arg := range args {
		if arg == "--debug" || arg == "-d" {
			logger.SetLevel(logger.DEBUG)
			fmt.Println("🔍 Debug mode enabled")
		}
		if arg == "--enable-web" {
			enableWeb = true
		}
	}

	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		os.Exit(1)
	}
	if enableWeb {
		cfg.Channels.Web.Enabled = true
	}

	provider, err := providers.CreateProvider(cfg)
	if err != nil {
		fmt.Printf("Error creating provider: %v\n", err)
		os.Exit(1)
	}

	msgBus := bus.NewMessageBus()

	var agentLoop *agent.AgentLoop
	var oracleConn *oracledb.ConnectionManager
	var oraStores *oracleStores

	if cfg.Oracle.Enabled {
		agentLoop, oracleConn, oraStores, err = initOracleAgent(cfg, msgBus, provider)
		if err != nil {
			fmt.Printf("Oracle initialization failed: %v\n", err)
			fmt.Println("Falling back to file-based storage...")
			agentLoop = agent.NewAgentLoop(cfg, msgBus, provider)
		} else {
			defer oracleConn.Close()
			fmt.Println("✓ Oracle AI Database storage enabled")
		}
	} else {
		agentLoop = agent.NewAgentLoop(cfg, msgBus, provider)
	}

	// Print agent startup info
	fmt.Println("\n📦 Agent Status:")
	startupInfo := agentLoop.GetStartupInfo()
	toolsInfo := startupInfo["tools"].(map[string]interface{})
	skillsInfo := startupInfo["skills"].(map[string]interface{})
	fmt.Printf("  • Tools: %d loaded\n", toolsInfo["count"])
	fmt.Printf("  • Skills: %d/%d available\n",
		skillsInfo["available"],
		skillsInfo["total"])

	// Log to file as well
	logger.InfoCF("agent", "Agent initialized",
		map[string]interface{}{
			"tools_count":      toolsInfo["count"],
			"skills_total":     skillsInfo["total"],
			"skills_available": skillsInfo["available"],
		})

	// Setup cron tool and service
	cronService := setupCronTool(agentLoop, msgBus, cfg.WorkspacePath(), cfg.Tools.Cron.ExecTimeoutMinutes)

	heartbeatService := heartbeat.NewHeartbeatService(
		cfg.WorkspacePath(),
		cfg.Heartbeat.Interval,
		cfg.Heartbeat.Enabled,
	)
	heartbeatService.SetBus(msgBus)
	heartbeatService.SetHandler(func(prompt, channel, chatID string) *tools.ToolResult {
		// Use cli:direct as fallback if no valid channel
		if channel == "" || chatID == "" {
			channel, chatID = "cli", "direct"
		}
		// Use ProcessHeartbeat - no session history, each heartbeat is independent
		response, err := agentLoop.ProcessHeartbeat(context.Background(), prompt, channel, chatID)
		if err != nil {
			return tools.ErrorResult(fmt.Sprintf("Heartbeat error: %v", err))
		}
		if response == "HEARTBEAT_OK" {
			return tools.SilentResult("Heartbeat OK")
		}
		// For heartbeat, always return silent - the subagent result will be
		// sent to user via processSystemMessage when the async task completes
		return tools.SilentResult(response)
	})

	channelManager, err := channels.NewManager(cfg, msgBus)
	if err != nil {
		fmt.Printf("Error creating channel manager: %v\n", err)
		os.Exit(1)
	}

	var transcriber *voice.GroqTranscriber
	if cfg.Providers.Groq.APIKey != "" {
		transcriber = voice.NewGroqTranscriber(cfg.Providers.Groq.APIKey)
		logger.InfoC("voice", "Groq voice transcription enabled")
	}

	if transcriber != nil {
		if telegramChannel, ok := channelManager.GetChannel("telegram"); ok {
			if tc, ok := telegramChannel.(*channels.TelegramChannel); ok {
				tc.SetTranscriber(transcriber)
				logger.InfoC("voice", "Groq transcription attached to Telegram channel")
			}
		}
		if discordChannel, ok := channelManager.GetChannel("discord"); ok {
			if dc, ok := discordChannel.(*channels.DiscordChannel); ok {
				dc.SetTranscriber(transcriber)
				logger.InfoC("voice", "Groq transcription attached to Discord channel")
			}
		}
		if slackChannel, ok := channelManager.GetChannel("slack"); ok {
			if sc, ok := slackChannel.(*channels.SlackChannel); ok {
				sc.SetTranscriber(transcriber)
				logger.InfoC("voice", "Groq transcription attached to Slack channel")
			}
		}
	}

	if cfg.Channels.Web.Enabled {
		if webChannel, ok := channelManager.GetChannel("web"); ok {
			if wc, ok := webChannel.(*web.Channel); ok {
				agentLoop.SetEventEmitter(wc)
				wc.SetSessions(&webSessionAdapter{})
				if oraStores != nil {
					wc.SetMemory(&webMemoryAdapter{m: oraStores.memory})
				}
				logger.InfoC("web", "Web channel wired (events + sessions + memory)")
			}
		}
	}

	enabledChannels := channelManager.GetEnabledChannels()
	if len(enabledChannels) > 0 {
		fmt.Printf("✓ Channels enabled: %s\n", enabledChannels)
	} else {
		fmt.Println("⚠ Warning: No channels enabled")
	}

	fmt.Printf("✓ Gateway started on %s:%d\n", cfg.Gateway.Host, cfg.Gateway.Port)
	fmt.Println("Press Ctrl+C to stop")

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := cronService.Start(); err != nil {
		fmt.Printf("Error starting cron service: %v\n", err)
	}
	fmt.Println("✓ Cron service started")

	if err := heartbeatService.Start(); err != nil {
		fmt.Printf("Error starting heartbeat service: %v\n", err)
	}
	fmt.Println("✓ Heartbeat service started")

	stateManager := state.NewManager(cfg.WorkspacePath())
	deviceService := devices.NewService(devices.Config{
		Enabled:    cfg.Devices.Enabled,
		MonitorUSB: cfg.Devices.MonitorUSB,
	}, stateManager)
	deviceService.SetBus(msgBus)
	if err := deviceService.Start(ctx); err != nil {
		fmt.Printf("Error starting device service: %v\n", err)
	} else if cfg.Devices.Enabled {
		fmt.Println("✓ Device event service started")
	}

	if err := channelManager.StartAll(ctx); err != nil {
		fmt.Printf("Error starting channels: %v\n", err)
	}

	healthServer := health.NewServer(cfg.Gateway.Host, cfg.Gateway.Port)
	go func() {
		if err := healthServer.Start(); err != nil && err != http.ErrServerClosed {
			logger.ErrorCF("health", "Health server error", map[string]interface{}{"error": err.Error()})
		}
	}()
	fmt.Printf("✓ Health endpoints available at http://%s:%d/health and /ready\n", cfg.Gateway.Host, cfg.Gateway.Port)

	go agentLoop.Run(ctx)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt)
	<-sigChan

	fmt.Println("\nShutting down...")
	cancel()
	healthServer.Stop(context.Background())
	deviceService.Stop()
	heartbeatService.Stop()
	cronService.Stop()
	agentLoop.Stop()
	channelManager.StopAll(ctx)
	fmt.Println("✓ Gateway stopped")
}

func statusCmd() {
	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		return
	}

	configPath := getConfigPath()

	fmt.Printf("%s picooraclaw Status\n", logo)
	fmt.Printf("Version: %s\n", formatVersion())
	build, _ := formatBuildInfo()
	if build != "" {
		fmt.Printf("Build: %s\n", build)
	}
	fmt.Println()

	if _, err := os.Stat(configPath); err == nil {
		fmt.Println("Config:", configPath, "✓")
	} else {
		fmt.Println("Config:", configPath, "✗")
	}

	workspace := cfg.WorkspacePath()
	if _, err := os.Stat(workspace); err == nil {
		fmt.Println("Workspace:", workspace, "✓")
	} else {
		fmt.Println("Workspace:", workspace, "✗")
	}

	if _, err := os.Stat(configPath); err == nil {
		fmt.Printf("Model: %s\n", cfg.Agents.Defaults.Model)

		hasOpenRouter := cfg.Providers.OpenRouter.APIKey != ""
		hasAnthropic := cfg.Providers.Anthropic.APIKey != ""
		hasOpenAI := cfg.Providers.OpenAI.APIKey != ""
		hasGemini := cfg.Providers.Gemini.APIKey != ""
		hasGroq := cfg.Providers.Groq.APIKey != ""
		hasOllama := cfg.Providers.Ollama.APIBase != "" || true // Ollama is always available locally
		hasVLLM := cfg.Providers.VLLM.APIBase != ""

		status := func(enabled bool) string {
			if enabled {
				return "✓"
			}
			return "not set"
		}
		fmt.Println("Ollama (default):", status(hasOllama))
		fmt.Println("OpenRouter API:", status(hasOpenRouter))
		fmt.Println("Anthropic API:", status(hasAnthropic))
		fmt.Println("OpenAI API:", status(hasOpenAI))
		fmt.Println("Gemini API:", status(hasGemini))
		fmt.Println("Groq API:", status(hasGroq))
		if hasVLLM {
			fmt.Printf("vLLM/Local: ✓ %s\n", cfg.Providers.VLLM.APIBase)
		} else {
			fmt.Println("vLLM/Local: not set")
		}

		store, _ := auth.LoadStore()
		if store != nil && len(store.Credentials) > 0 {
			fmt.Println("\nOAuth/Token Auth:")
			for provider, cred := range store.Credentials {
				status := "authenticated"
				if cred.IsExpired() {
					status = "expired"
				} else if cred.NeedsRefresh() {
					status = "needs refresh"
				}
				fmt.Printf("  %s (%s): %s\n", provider, cred.AuthMethod, status)
			}
		}
	}
}

func authCmd() {
	if len(os.Args) < 3 {
		authHelp()
		return
	}

	switch os.Args[2] {
	case "login":
		authLoginCmd()
	case "logout":
		authLogoutCmd()
	case "status":
		authStatusCmd()
	default:
		fmt.Printf("Unknown auth command: %s\n", os.Args[2])
		authHelp()
	}
}

func authHelp() {
	fmt.Println("\nAuth commands:")
	fmt.Println("  login       Login via OAuth or paste token")
	fmt.Println("  logout      Remove stored credentials")
	fmt.Println("  status      Show current auth status")
	fmt.Println()
	fmt.Println("Login options:")
	fmt.Println("  --provider <name>    Provider to login with (openai, anthropic)")
	fmt.Println("  --device-code        Use device code flow (for headless environments)")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  picooraclaw auth login --provider openai")
	fmt.Println("  picooraclaw auth login --provider openai --device-code")
	fmt.Println("  picooraclaw auth login --provider anthropic")
	fmt.Println("  picoclaw auth logout --provider openai")
	fmt.Println("  picoclaw auth status")
}

func authLoginCmd() {
	provider := ""
	useDeviceCode := false

	args := os.Args[3:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--provider", "-p":
			if i+1 < len(args) {
				provider = args[i+1]
				i++
			}
		case "--device-code":
			useDeviceCode = true
		}
	}

	if provider == "" {
		fmt.Println("Error: --provider is required")
		fmt.Println("Supported providers: openai, anthropic")
		return
	}

	switch provider {
	case "openai":
		authLoginOpenAI(useDeviceCode)
	case "anthropic":
		authLoginPasteToken(provider)
	default:
		fmt.Printf("Unsupported provider: %s\n", provider)
		fmt.Println("Supported providers: openai, anthropic")
	}
}

func authLoginOpenAI(useDeviceCode bool) {
	cfg := auth.OpenAIOAuthConfig()

	var cred *auth.AuthCredential
	var err error

	if useDeviceCode {
		cred, err = auth.LoginDeviceCode(cfg)
	} else {
		cred, err = auth.LoginBrowser(cfg)
	}

	if err != nil {
		fmt.Printf("Login failed: %v\n", err)
		os.Exit(1)
	}

	if err := auth.SetCredential("openai", cred); err != nil {
		fmt.Printf("Failed to save credentials: %v\n", err)
		os.Exit(1)
	}

	appCfg, err := loadConfig()
	if err == nil {
		appCfg.Providers.OpenAI.AuthMethod = "oauth"
		if err := config.SaveConfig(getConfigPath(), appCfg); err != nil {
			fmt.Printf("Warning: could not update config: %v\n", err)
		}
	}

	fmt.Println("Login successful!")
	if cred.AccountID != "" {
		fmt.Printf("Account: %s\n", cred.AccountID)
	}
}

func authLoginPasteToken(provider string) {
	cred, err := auth.LoginPasteToken(provider, os.Stdin)
	if err != nil {
		fmt.Printf("Login failed: %v\n", err)
		os.Exit(1)
	}

	if err := auth.SetCredential(provider, cred); err != nil {
		fmt.Printf("Failed to save credentials: %v\n", err)
		os.Exit(1)
	}

	appCfg, err := loadConfig()
	if err == nil {
		switch provider {
		case "anthropic":
			appCfg.Providers.Anthropic.AuthMethod = "token"
		case "openai":
			appCfg.Providers.OpenAI.AuthMethod = "token"
		}
		if err := config.SaveConfig(getConfigPath(), appCfg); err != nil {
			fmt.Printf("Warning: could not update config: %v\n", err)
		}
	}

	fmt.Printf("Token saved for %s!\n", provider)
}

func authLogoutCmd() {
	provider := ""

	args := os.Args[3:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--provider", "-p":
			if i+1 < len(args) {
				provider = args[i+1]
				i++
			}
		}
	}

	if provider != "" {
		if err := auth.DeleteCredential(provider); err != nil {
			fmt.Printf("Failed to remove credentials: %v\n", err)
			os.Exit(1)
		}

		appCfg, err := loadConfig()
		if err == nil {
			switch provider {
			case "openai":
				appCfg.Providers.OpenAI.AuthMethod = ""
			case "anthropic":
				appCfg.Providers.Anthropic.AuthMethod = ""
			}
			config.SaveConfig(getConfigPath(), appCfg)
		}

		fmt.Printf("Logged out from %s\n", provider)
	} else {
		if err := auth.DeleteAllCredentials(); err != nil {
			fmt.Printf("Failed to remove credentials: %v\n", err)
			os.Exit(1)
		}

		appCfg, err := loadConfig()
		if err == nil {
			appCfg.Providers.OpenAI.AuthMethod = ""
			appCfg.Providers.Anthropic.AuthMethod = ""
			config.SaveConfig(getConfigPath(), appCfg)
		}

		fmt.Println("Logged out from all providers")
	}
}

func authStatusCmd() {
	store, err := auth.LoadStore()
	if err != nil {
		fmt.Printf("Error loading auth store: %v\n", err)
		return
	}

	// Check Ollama availability (local, no auth required).
	ollamaBase := "http://localhost:11434"
	cfg, cfgErr := loadConfig()
	if cfgErr == nil && cfg.Providers.Ollama.APIBase != "" {
		ollamaBase = cfg.Providers.Ollama.APIBase
	}
	ollamaOK := false
	httpClient := &http.Client{Timeout: 2 * time.Second}
	if resp, err := httpClient.Get(ollamaBase); err == nil {
		resp.Body.Close()
		ollamaOK = true
	}

	hasOAuth := len(store.Credentials) > 0

	if !hasOAuth && !ollamaOK {
		fmt.Println("No authenticated providers.")
		fmt.Println("Run: picooraclaw auth login --provider <name>")
		return
	}

	fmt.Println("\nAuthenticated Providers:")
	fmt.Println("------------------------")

	if ollamaOK {
		fmt.Printf("  ollama:\n")
		fmt.Printf("    Method: local\n")
		fmt.Printf("    Status: active\n")
		fmt.Printf("    Endpoint: %s\n", ollamaBase)
	}

	for provider, cred := range store.Credentials {
		status := "active"
		if cred.IsExpired() {
			status = "expired"
		} else if cred.NeedsRefresh() {
			status = "needs refresh"
		}

		fmt.Printf("  %s:\n", provider)
		fmt.Printf("    Method: %s\n", cred.AuthMethod)
		fmt.Printf("    Status: %s\n", status)
		if cred.AccountID != "" {
			fmt.Printf("    Account: %s\n", cred.AccountID)
		}
		if !cred.ExpiresAt.IsZero() {
			fmt.Printf("    Expires: %s\n", cred.ExpiresAt.Format("2006-01-02 15:04"))
		}
	}
}

func getConfigPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".picooraclaw", "config.json")
}

func setupCronTool(agentLoop *agent.AgentLoop, msgBus *bus.MessageBus, workspace string, execTimeoutMinutes int) *cron.CronService {
	cronStorePath := filepath.Join(workspace, "cron", "jobs.json")

	// Create cron service
	cronService := cron.NewCronService(cronStorePath, nil)

	// Compute exec timeout (0 minutes = no timeout)
	execTimeout := time.Duration(execTimeoutMinutes) * time.Minute

	// Create and register CronTool
	cronTool := tools.NewCronTool(cronService, agentLoop, msgBus, workspace, execTimeout)
	agentLoop.RegisterTool(cronTool)

	// Set the onJob handler
	cronService.SetOnJob(func(job *cron.CronJob) (string, error) {
		result := cronTool.ExecuteJob(context.Background(), job)
		return result, nil
	})

	return cronService
}

func loadConfig() (*config.Config, error) {
	return config.LoadConfig(getConfigPath())
}

func cronCmd() {
	if len(os.Args) < 3 {
		cronHelp()
		return
	}

	subcommand := os.Args[2]

	// Load config to get workspace path
	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		return
	}

	cronStorePath := filepath.Join(cfg.WorkspacePath(), "cron", "jobs.json")

	switch subcommand {
	case "list":
		cronListCmd(cronStorePath)
	case "add":
		cronAddCmd(cronStorePath)
	case "remove":
		if len(os.Args) < 4 {
			fmt.Println("Usage: picoclaw cron remove <job_id>")
			return
		}
		cronRemoveCmd(cronStorePath, os.Args[3])
	case "enable":
		cronEnableCmd(cronStorePath, false)
	case "disable":
		cronEnableCmd(cronStorePath, true)
	default:
		fmt.Printf("Unknown cron command: %s\n", subcommand)
		cronHelp()
	}
}

func cronHelp() {
	fmt.Println("\nCron commands:")
	fmt.Println("  list              List all scheduled jobs")
	fmt.Println("  add              Add a new scheduled job")
	fmt.Println("  remove <id>       Remove a job by ID")
	fmt.Println("  enable <id>      Enable a job")
	fmt.Println("  disable <id>     Disable a job")
	fmt.Println()
	fmt.Println("Add options:")
	fmt.Println("  -n, --name       Job name")
	fmt.Println("  -m, --message    Message for agent")
	fmt.Println("  -e, --every      Run every N seconds")
	fmt.Println("  -c, --cron       Cron expression (e.g. '0 9 * * *')")
	fmt.Println("  -d, --deliver     Deliver response to channel")
	fmt.Println("  --to             Recipient for delivery")
	fmt.Println("  --channel        Channel for delivery")
}

func cronListCmd(storePath string) {
	cs := cron.NewCronService(storePath, nil)
	jobs := cs.ListJobs(true) // Show all jobs, including disabled

	if len(jobs) == 0 {
		fmt.Println("No scheduled jobs.")
		return
	}

	fmt.Println("\nScheduled Jobs:")
	fmt.Println("----------------")
	for _, job := range jobs {
		var schedule string
		if job.Schedule.Kind == "every" && job.Schedule.EveryMS != nil {
			schedule = fmt.Sprintf("every %ds", *job.Schedule.EveryMS/1000)
		} else if job.Schedule.Kind == "cron" {
			schedule = job.Schedule.Expr
		} else {
			schedule = "one-time"
		}

		nextRun := "scheduled"
		if job.State.NextRunAtMS != nil {
			nextTime := time.UnixMilli(*job.State.NextRunAtMS)
			nextRun = nextTime.Format("2006-01-02 15:04")
		}

		status := "enabled"
		if !job.Enabled {
			status = "disabled"
		}

		fmt.Printf("  %s (%s)\n", job.Name, job.ID)
		fmt.Printf("    Schedule: %s\n", schedule)
		fmt.Printf("    Status: %s\n", status)
		fmt.Printf("    Next run: %s\n", nextRun)
	}
}

func cronAddCmd(storePath string) {
	name := ""
	message := ""
	var everySec *int64
	cronExpr := ""
	deliver := false
	channel := ""
	to := ""

	args := os.Args[3:]
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "-n", "--name":
			if i+1 < len(args) {
				name = args[i+1]
				i++
			}
		case "-m", "--message":
			if i+1 < len(args) {
				message = args[i+1]
				i++
			}
		case "-e", "--every":
			if i+1 < len(args) {
				var sec int64
				fmt.Sscanf(args[i+1], "%d", &sec)
				everySec = &sec
				i++
			}
		case "-c", "--cron":
			if i+1 < len(args) {
				cronExpr = args[i+1]
				i++
			}
		case "-d", "--deliver":
			deliver = true
		case "--to":
			if i+1 < len(args) {
				to = args[i+1]
				i++
			}
		case "--channel":
			if i+1 < len(args) {
				channel = args[i+1]
				i++
			}
		}
	}

	if name == "" {
		fmt.Println("Error: --name is required")
		return
	}

	if message == "" {
		fmt.Println("Error: --message is required")
		return
	}

	if everySec == nil && cronExpr == "" {
		fmt.Println("Error: Either --every or --cron must be specified")
		return
	}

	var schedule cron.CronSchedule
	if everySec != nil {
		everyMS := *everySec * 1000
		schedule = cron.CronSchedule{
			Kind:    "every",
			EveryMS: &everyMS,
		}
	} else {
		schedule = cron.CronSchedule{
			Kind: "cron",
			Expr: cronExpr,
		}
	}

	cs := cron.NewCronService(storePath, nil)
	job, err := cs.AddJob(name, schedule, message, deliver, channel, to)
	if err != nil {
		fmt.Printf("Error adding job: %v\n", err)
		return
	}

	fmt.Printf("✓ Added job '%s' (%s)\n", job.Name, job.ID)
}

func cronRemoveCmd(storePath, jobID string) {
	cs := cron.NewCronService(storePath, nil)
	if cs.RemoveJob(jobID) {
		fmt.Printf("✓ Removed job %s\n", jobID)
	} else {
		fmt.Printf("✗ Job %s not found\n", jobID)
	}
}

func cronEnableCmd(storePath string, disable bool) {
	if len(os.Args) < 4 {
		fmt.Println("Usage: picoclaw cron enable/disable <job_id>")
		return
	}

	jobID := os.Args[3]
	cs := cron.NewCronService(storePath, nil)
	enabled := !disable

	job := cs.EnableJob(jobID, enabled)
	if job != nil {
		status := "enabled"
		if disable {
			status = "disabled"
		}
		fmt.Printf("✓ Job '%s' %s\n", job.Name, status)
	} else {
		fmt.Printf("✗ Job %s not found\n", jobID)
	}
}

func skillsHelp() {
	fmt.Println("\nSkills commands:")
	fmt.Println("  list                    List installed skills")
	fmt.Println("  install <repo>          Install skill from GitHub")
	fmt.Println("  install-builtin          Install all builtin skills to workspace")
	fmt.Println("  list-builtin             List available builtin skills")
	fmt.Println("  remove <name>           Remove installed skill")
	fmt.Println("  search                  Search available skills")
	fmt.Println("  show <name>             Show skill details")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  picoclaw skills list")
	fmt.Println("  picoclaw skills install sipeed/picoclaw-skills/weather")
	fmt.Println("  picoclaw skills install-builtin")
	fmt.Println("  picoclaw skills list-builtin")
	fmt.Println("  picoclaw skills remove weather")
}

func skillsListCmd(loader *skills.SkillsLoader) {
	allSkills := loader.ListSkills()

	if len(allSkills) == 0 {
		fmt.Println("No skills installed.")
		return
	}

	fmt.Println("\nInstalled Skills:")
	fmt.Println("------------------")
	for _, skill := range allSkills {
		fmt.Printf("  ✓ %s (%s)\n", skill.Name, skill.Source)
		if skill.Description != "" {
			fmt.Printf("    %s\n", skill.Description)
		}
	}
}

func skillsInstallCmd(installer *skills.SkillInstaller) {
	if len(os.Args) < 4 {
		fmt.Println("Usage: picoclaw skills install <github-repo>")
		fmt.Println("Example: picoclaw skills install sipeed/picoclaw-skills/weather")
		return
	}

	repo := os.Args[3]
	fmt.Printf("Installing skill from %s...\n", repo)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := installer.InstallFromGitHub(ctx, repo); err != nil {
		fmt.Printf("✗ Failed to install skill: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Skill '%s' installed successfully!\n", filepath.Base(repo))
}

func skillsRemoveCmd(installer *skills.SkillInstaller, skillName string) {
	fmt.Printf("Removing skill '%s'...\n", skillName)

	if err := installer.Uninstall(skillName); err != nil {
		fmt.Printf("✗ Failed to remove skill: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✓ Skill '%s' removed successfully!\n", skillName)
}

func skillsInstallBuiltinCmd(workspace string) {
	workspaceSkillsDir := filepath.Join(workspace, "skills")
	embeddedSkillsRoot := "workspace/skills"

	fmt.Printf("Copying builtin skills to workspace...\n")

	entries, err := embeddedFiles.ReadDir(embeddedSkillsRoot)
	if err != nil {
		fmt.Printf("✗ Could not read embedded skills: %v\n", err)
		return
	}

	installed := 0
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		skillName := entry.Name()
		workspacePath := filepath.Join(workspaceSkillsDir, skillName)

		// Walk embedded skill directory and write each file out.
		skillEmbedPath := embeddedSkillsRoot + "/" + skillName
		writeErr := false
		_ = fs.WalkDir(embeddedFiles, skillEmbedPath, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}
			rel, _ := filepath.Rel(skillEmbedPath, path)
			dst := filepath.Join(workspacePath, rel)
			if d.IsDir() {
				return os.MkdirAll(dst, 0755)
			}
			data, err := embeddedFiles.ReadFile(path)
			if err != nil {
				return err
			}
			if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
				return err
			}
			return os.WriteFile(dst, data, 0644)
		})
		if writeErr {
			fmt.Printf("✗ Failed to install skill '%s'\n", skillName)
			continue
		}
		fmt.Printf("✓ Installed builtin skill '%s'\n", skillName)
		installed++
	}

	fmt.Printf("\n✓ %d builtin skills installed to workspace.\n", installed)
}

func skillsListBuiltinCmd() {
	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		return
	}
	builtinSkillsDir := filepath.Join(filepath.Dir(cfg.WorkspacePath()), "picoclaw", "skills")

	fmt.Println("\nAvailable Builtin Skills:")
	fmt.Println("-----------------------")

	entries, err := os.ReadDir(builtinSkillsDir)
	if err != nil {
		fmt.Printf("Error reading builtin skills: %v\n", err)
		return
	}

	if len(entries) == 0 {
		fmt.Println("No builtin skills available.")
		return
	}

	for _, entry := range entries {
		if entry.IsDir() {
			skillName := entry.Name()
			skillFile := filepath.Join(builtinSkillsDir, skillName, "SKILL.md")

			description := "No description"
			if _, err := os.Stat(skillFile); err == nil {
				data, err := os.ReadFile(skillFile)
				if err == nil {
					content := string(data)
					if idx := strings.Index(content, "\n"); idx > 0 {
						firstLine := content[:idx]
						if strings.Contains(firstLine, "description:") {
							descLine := strings.Index(content[idx:], "\n")
							if descLine > 0 {
								description = strings.TrimSpace(content[idx+descLine : idx+descLine])
							}
						}
					}
				}
			}
			status := "✓"
			fmt.Printf("  %s  %s\n", status, entry.Name())
			if description != "" {
				fmt.Printf("     %s\n", description)
			}
		}
	}
}

func skillsSearchCmd(installer *skills.SkillInstaller) {
	fmt.Println("Searching for available skills...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	availableSkills, err := installer.ListAvailableSkills(ctx)
	if err != nil {
		fmt.Printf("✗ Failed to fetch skills list: %v\n", err)
		return
	}

	if len(availableSkills) == 0 {
		fmt.Println("No skills available.")
		return
	}

	fmt.Printf("\nAvailable Skills (%d):\n", len(availableSkills))
	fmt.Println("--------------------")
	for _, skill := range availableSkills {
		fmt.Printf("  📦 %s\n", skill.Name)
		fmt.Printf("     %s\n", skill.Description)
		fmt.Printf("     Repo: %s\n", skill.Repository)
		if skill.Author != "" {
			fmt.Printf("     Author: %s\n", skill.Author)
		}
		if len(skill.Tags) > 0 {
			fmt.Printf("     Tags: %v\n", skill.Tags)
		}
		fmt.Println()
	}
}

func skillsShowCmd(loader *skills.SkillsLoader, skillName string) {
	content, ok := loader.LoadSkill(skillName)
	if !ok {
		fmt.Printf("✗ Skill '%s' not found\n", skillName)
		return
	}

	fmt.Printf("\n📦 Skill: %s\n", skillName)
	fmt.Println("----------------------")
	fmt.Println(content)
}

// setupOracleCmd initializes Oracle schema and loads the ONNX model.
func setupOracleCmd() {
	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		os.Exit(1)
	}

	if !cfg.Oracle.Enabled {
		fmt.Println("Oracle is not enabled in config. Set oracle.enabled = true first.")
		os.Exit(1)
	}

	fmt.Println("🔧 Setting up Oracle Database for picooraclaw...")

	// Connect
	conn, err := oracledb.NewConnectionManager(&cfg.Oracle)
	if err != nil {
		fmt.Printf("✗ Connection failed: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()
	fmt.Println("✓ Connected to Oracle Database")

	// Init schema
	if err := oracledb.InitSchema(conn.DB()); err != nil {
		fmt.Printf("✗ Schema initialization failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("✓ Schema initialized (8 tables with PICO_ prefix)")

	// Set up embedding service
	var embSvc *oracledb.EmbeddingService
	if cfg.Oracle.EmbeddingProvider == "api" && cfg.Oracle.EmbeddingAPIKey != "" {
		embSvc = oracledb.NewAPIEmbeddingService(conn.DB(), cfg.Oracle.EmbeddingAPIBase, cfg.Oracle.EmbeddingAPIKey, cfg.Oracle.EmbeddingModel)
		fmt.Printf("✓ Using API embedding provider (model: %s)\n", cfg.Oracle.EmbeddingModel)
	} else {
		var embErr error
		embSvc, embErr = oracledb.NewEmbeddingService(conn.DB(), cfg.Oracle.ONNXModel)
		if embErr != nil {
			fmt.Printf("✗ Failed to create embedding service: %v\n", embErr)
			os.Exit(1)
		}
		loaded, err := embSvc.CheckONNXLoaded()
		if err != nil {
			fmt.Printf("⚠ Could not check ONNX model status: %v\n", err)
		}

		if loaded {
			fmt.Printf("✓ ONNX model '%s' already loaded\n", cfg.Oracle.ONNXModel)
		} else {
			fmt.Printf("Loading ONNX model '%s'...\n", cfg.Oracle.ONNXModel)

			onnxDir := "PICO_ONNX_DIR"
			onnxFile := "all_MiniLM_L12_v2.onnx"

			// Parse optional args
			args := os.Args[2:]
			for i := 0; i < len(args); i++ {
				switch args[i] {
				case "--onnx-dir":
					if i+1 < len(args) {
						onnxDir = args[i+1]
						i++
					}
				case "--onnx-file":
					if i+1 < len(args) {
						onnxFile = args[i+1]
						i++
					}
				}
			}

			if err := embSvc.LoadONNXModel(onnxDir, onnxFile); err != nil {
				fmt.Printf("✗ ONNX model load failed: %v\n", err)
				fmt.Println("  You may need to manually load the ONNX model.")
				fmt.Println("  See: https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/")
			} else {
				fmt.Printf("✓ ONNX model '%s' loaded\n", cfg.Oracle.ONNXModel)
			}
		}
	}

	// Test embedding
	if embSvc.TestEmbedding() {
		fmt.Printf("✓ Embedding test passed (mode: %s)\n", embSvc.Mode())
	} else {
		fmt.Printf("⚠ Embedding test failed (mode: %s)\n", embSvc.Mode())
	}

	// Seed prompts from workspace
	promptStore := oracledb.NewPromptStore(conn.DB(), cfg.Oracle.AgentID)
	workspace := cfg.WorkspacePath()
	if err := promptStore.SeedFromWorkspace(workspace); err != nil {
		fmt.Printf("⚠ Prompt seeding warning: %v\n", err)
	} else {
		fmt.Println("✓ Prompts seeded from workspace")
	}

	fmt.Println("\n🎉 Oracle setup complete! picooraclaw is ready to use Oracle AI Database.")
}

// oracleStores bundles Oracle-backed stores exposed to gatewayCmd so downstream
// wiring (web channel adapters, etc.) can reach the memory store directly.
type oracleStores struct {
	session *oracledb.SessionStore
	memory  *oracledb.MemoryStore
}

// initOracleAgent creates an agent loop with Oracle-backed stores.
func initOracleAgent(cfg *config.Config, msgBus *bus.MessageBus, provider providers.LLMProvider) (*agent.AgentLoop, *oracledb.ConnectionManager, *oracleStores, error) {
	conn, err := oracledb.NewConnectionManager(&cfg.Oracle)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("Oracle connection failed: %w", err)
	}

	db := conn.DB()
	agentID := cfg.Oracle.AgentID

	// Create embedding service (API mode or in-database ONNX mode)
	var embSvc *oracledb.EmbeddingService
	if cfg.Oracle.EmbeddingProvider == "api" && cfg.Oracle.EmbeddingAPIKey != "" {
		embSvc = oracledb.NewAPIEmbeddingService(db, cfg.Oracle.EmbeddingAPIBase, cfg.Oracle.EmbeddingAPIKey, cfg.Oracle.EmbeddingModel)
		logger.InfoC("oracle", "Using API-based embedding service")
	} else {
		var embErr error
		embSvc, embErr = oracledb.NewEmbeddingService(db, cfg.Oracle.ONNXModel)
		if embErr != nil {
			logger.ErrorCF("oracle", "Failed to create embedding service", map[string]interface{}{"error": embErr.Error()})
			return nil, nil, nil, fmt.Errorf("failed to create embedding service: %w", embErr)
		}
		logger.InfoC("oracle", "Using in-database ONNX embedding service")
	}

	// Create Oracle stores
	sessionStore := oracledb.NewSessionStore(db, agentID)
	stateStore := oracledb.NewStateStore(db, agentID)
	memoryStore := oracledb.NewMemoryStore(db, agentID, embSvc)

	// Create agent loop with Oracle stores
	agentLoop := agent.NewAgentLoopWithStores(cfg, msgBus, provider, sessionStore, stateStore, memoryStore)

	// Register remember/recall/daily-note tools
	agentLoop.RegisterTool(tools.NewRememberTool(memoryStore))
	agentLoop.RegisterTool(tools.NewWriteDailyNoteTool(memoryStore))

	// Create a recall adapter that bridges oracle.MemoryRecallResult to tools.RecallResult
	agentLoop.RegisterTool(tools.NewRecallTool(&recallAdapter{store: memoryStore}))

	// Wire prompt store into context builder for Oracle-backed prompts
	promptStore := oracledb.NewPromptStore(db, agentID)
	agentLoop.SetPromptStore(promptStore)

	logger.InfoC("oracle", "Oracle stores initialized")
	return agentLoop, conn, &oracleStores{session: sessionStore, memory: memoryStore}, nil
}

// recallAdapter adapts oracle.MemoryStore to tools.Recaller interface.
type recallAdapter struct {
	store *oracledb.MemoryStore
}

func (a *recallAdapter) Recall(query string, maxResults int) ([]tools.RecallResult, error) {
	oracleResults, err := a.store.Recall(query, maxResults)
	if err != nil {
		return nil, err
	}

	results := make([]tools.RecallResult, len(oracleResults))
	for i, r := range oracleResults {
		results[i] = tools.RecallResult{
			MemoryID:   r.MemoryID,
			Text:       r.Text,
			Importance: r.Importance,
			Category:   r.Category,
			Score:      r.Score,
		}
	}
	return results, nil
}

// oracleInspectCmd shows all data stored in Oracle Database.
func oracleInspectCmd() {
	cfg, err := loadConfig()
	if err != nil {
		fmt.Printf("Error loading config: %v\n", err)
		os.Exit(1)
	}

	if !cfg.Oracle.Enabled {
		fmt.Println("Oracle is not enabled in config. Set oracle.enabled = true first.")
		os.Exit(1)
	}

	// Parse subcommand and flags
	filter := ""
	subFilter := "" // secondary positional arg (e.g. prompt name)
	searchQuery := ""
	limit := 20
	if len(os.Args) > 2 {
		for i := 2; i < len(os.Args); i++ {
			switch os.Args[i] {
			case "--help", "-h":
				oracleInspectHelp()
				return
			case "--limit", "-n":
				if i+1 < len(os.Args) {
					fmt.Sscanf(os.Args[i+1], "%d", &limit)
					i++
				}
			case "--search", "-s":
				if i+1 < len(os.Args) {
					searchQuery = os.Args[i+1]
					i++
				}
			default:
				if !strings.HasPrefix(os.Args[i], "-") {
					if filter == "" {
						filter = os.Args[i]
					} else if subFilter == "" {
						subFilter = os.Args[i]
					}
				}
			}
		}
	}

	conn, err := oracledb.NewConnectionManager(&cfg.Oracle)
	if err != nil {
		fmt.Printf("Connection failed: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()

	db := conn.DB()

	switch filter {
	case "":
		inspectOverview(db, cfg.Oracle.AgentID)
	case "memories":
		inspectMemories(db, cfg.Oracle.AgentID, limit, searchQuery, &cfg.Oracle)
	case "sessions":
		inspectSessions(db, cfg.Oracle.AgentID, limit)
	case "transcripts":
		inspectTranscripts(db, cfg.Oracle.AgentID, limit)
	case "state":
		inspectState(db, cfg.Oracle.AgentID)
	case "notes":
		inspectDailyNotes(db, cfg.Oracle.AgentID, limit)
	case "prompts":
		inspectPrompts(db, cfg.Oracle.AgentID, subFilter)
	case "config":
		inspectConfig(db, cfg.Oracle.AgentID)
	case "meta":
		inspectMeta(db)
	default:
		fmt.Printf("Unknown table: %s\n", filter)
		oracleInspectHelp()
	}
}

func oracleInspectHelp() {
	fmt.Println("\nInspect data stored in Oracle Database")
	fmt.Println()
	fmt.Println("Usage: picooraclaw oracle-inspect [table] [options]")
	fmt.Println()
	fmt.Println("Tables:")
	fmt.Println("  (none)        Show overview with row counts for all tables")
	fmt.Println("  memories      Show stored memories with embeddings")
	fmt.Println("  sessions      Show chat sessions")
	fmt.Println("  transcripts   Show conversation transcripts")
	fmt.Println("  state         Show key-value state entries")
	fmt.Println("  notes         Show daily notes")
	fmt.Println("  prompts [name]  Show system prompts (add name to view full content: IDENTITY, SOUL, AGENT, USER, TOOLS)")
	fmt.Println("  config        Show stored config entries")
	fmt.Println("  meta          Show schema metadata")
	fmt.Println()
	fmt.Println("Options:")
	fmt.Println("  -n, --limit <N>      Max rows to display (default: 20)")
	fmt.Println("  -s, --search <text>  Semantic search (memories only)")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  picooraclaw oracle-inspect                         # Overview dashboard")
	fmt.Println("  picooraclaw oracle-inspect memories                # List all memories")
	fmt.Println("  picooraclaw oracle-inspect memories -s \"Go lang\"   # Semantic search")
	fmt.Println("  picooraclaw oracle-inspect transcripts -n 50       # Last 50 transcript lines")
}

// inspectOverview shows row counts and a summary for all PICO_ tables.
func inspectOverview(db *sql.DB, agentID string) {
	fmt.Println()
	fmt.Println("=============================================================")
	fmt.Println("  PicoOraClaw Oracle AI Database Inspector")
	fmt.Println("=============================================================")
	fmt.Println()

	tables := []struct {
		name  string
		label string
	}{
		{"PICO_MEMORIES", "Memories"},
		{"PICO_SESSIONS", "Sessions"},
		{"PICO_TRANSCRIPTS", "Transcripts"},
		{"PICO_STATE", "State"},
		{"PICO_DAILY_NOTES", "Daily Notes"},
		{"PICO_PROMPTS", "Prompts"},
		{"PICO_CONFIG", "Config"},
		{"PICO_META", "Meta"},
	}

	fmt.Println("  Table                  Rows")
	fmt.Println("  ─────────────────────  ────")

	totalRows := 0
	for _, t := range tables {
		var count int
		err := db.QueryRow(fmt.Sprintf("SELECT COUNT(*) FROM %s", t.name)).Scan(&count)
		if err != nil {
			fmt.Printf("  %-23s  error: %v\n", t.label, err)
			continue
		}
		totalRows += count
		bar := strings.Repeat("█", min(count, 40))
		if count > 0 {
			fmt.Printf("  %-23s %4d  %s\n", t.label, count, bar)
		} else {
			fmt.Printf("  %-23s %4d  (empty)\n", t.label, count)
		}
	}

	fmt.Println("  ─────────────────────  ────")
	fmt.Printf("  %-23s %4d\n", "Total", totalRows)

	// Show latest memories
	fmt.Println()
	fmt.Println("  Recent Memories (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows, err := db.Query(`
		SELECT memory_id, content, importance, category,
		       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created
		FROM PICO_MEMORIES
		WHERE agent_id = :1
		ORDER BY created_at DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows.Close()
		hasRows := false
		for rows.Next() {
			hasRows = true
			var memID, created string
			var content, category sql.NullString
			var importance float64
			if err := rows.Scan(&memID, &content, &importance, &category, &created); err != nil {
				continue
			}
			text := "(empty)"
			if content.Valid {
				text = content.String
			}
			cat := ""
			if category.Valid && category.String != "" {
				cat = fmt.Sprintf(" [%s]", category.String)
			}
			fmt.Printf("  %s  %.1f%s  %s\n", created, importance, cat, text)
		}
		if !hasRows {
			fmt.Println("  (no memories stored yet)")
		}
	}

	// Show latest transcript entries
	fmt.Println()
	fmt.Println("  Recent Transcripts (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows2, err := db.Query(`
		SELECT role, content,
		       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created
		FROM PICO_TRANSCRIPTS
		WHERE agent_id = :1
		ORDER BY id DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows2.Close()
		hasRows := false
		for rows2.Next() {
			hasRows = true
			var role, created string
			var content sql.NullString
			if err := rows2.Scan(&role, &content, &created); err != nil {
				continue
			}
			text := "(empty)"
			if content.Valid {
				text = content.String
			}
			fmt.Printf("  %s  %-10s  %s\n", created, role, text)
		}
		if !hasRows {
			fmt.Println("  (no transcripts yet)")
		}
	}

	// Show latest sessions
	fmt.Println()
	fmt.Println("  Recent Sessions (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows3, err := db.Query(`
		SELECT session_key, summary,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_SESSIONS
		WHERE agent_id = :1
		ORDER BY updated_at DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows3.Close()
		hasRows := false
		for rows3.Next() {
			hasRows = true
			var sessionKey, updated string
			var summary sql.NullString
			if err := rows3.Scan(&sessionKey, &summary, &updated); err != nil {
				continue
			}
			sumText := "(no summary)"
			if summary.Valid && summary.String != "" {
				sumText = summary.String
			}
			fmt.Printf("  %s  %-30s  %s\n", updated, sessionKey, sumText)
		}
		if !hasRows {
			fmt.Println("  (no sessions yet)")
		}
	}

	// Show state entries (last 5 by updated_at)
	fmt.Println()
	fmt.Println("  Recent State Entries (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows4, err := db.Query(`
		SELECT state_key, state_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_STATE
		WHERE agent_id = :1
		ORDER BY updated_at DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows4.Close()
		hasRows := false
		for rows4.Next() {
			hasRows = true
			var key, updated string
			var value sql.NullString
			if err := rows4.Scan(&key, &value, &updated); err != nil {
				continue
			}
			val := "(null)"
			if value.Valid {
				val = value.String
			}
			fmt.Printf("  %s  %-25s = %s\n", updated, key, val)
		}
		if !hasRows {
			fmt.Println("  (no state entries yet)")
		}
	}

	// Show latest daily notes
	fmt.Println()
	fmt.Println("  Recent Daily Notes (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows5, err := db.Query(`
		SELECT TO_CHAR(note_date, 'YYYY-MM-DD') AS note_day, content,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_DAILY_NOTES
		WHERE agent_id = :1
		ORDER BY note_date DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows5.Close()
		hasRows := false
		for rows5.Next() {
			hasRows = true
			var noteDay, updated string
			var content sql.NullString
			if err := rows5.Scan(&noteDay, &content, &updated); err != nil {
				continue
			}
			text := "(empty)"
			if content.Valid {
				text = content.String
			}
			fmt.Printf("  %s  (updated %s)  %s\n", noteDay, updated, text)
		}
		if !hasRows {
			fmt.Println("  (no daily notes yet)")
		}
	}

	// Show prompts
	fmt.Println()
	fmt.Println("  System Prompts (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows6, err := db.Query(`
		SELECT prompt_name, DBMS_LOB.GETLENGTH(content) AS content_len,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_PROMPTS
		WHERE agent_id = :1
		ORDER BY updated_at DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows6.Close()
		hasRows := false
		for rows6.Next() {
			hasRows = true
			var name, updated string
			var contentLen sql.NullInt64
			if err := rows6.Scan(&name, &contentLen, &updated); err != nil {
				continue
			}
			size := int64(0)
			if contentLen.Valid {
				size = contentLen.Int64
			}
			fmt.Printf("  %s  %-25s  %d chars\n", updated, name, size)
		}
		if !hasRows {
			fmt.Println("  (no prompts stored yet)")
		}
	}

	// Show config entries
	fmt.Println()
	fmt.Println("  Config Entries (last 5):")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows7, err := db.Query(`
		SELECT config_key, config_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_CONFIG
		WHERE agent_id = :1
		ORDER BY updated_at DESC
		FETCH FIRST 5 ROWS ONLY`, agentID)
	if err == nil {
		defer rows7.Close()
		hasRows := false
		for rows7.Next() {
			hasRows = true
			var key, updated string
			var value sql.NullString
			if err := rows7.Scan(&key, &value, &updated); err != nil {
				continue
			}
			val := "(null)"
			if value.Valid {
				val = value.String
			}
			fmt.Printf("  %s  %-25s = %s\n", updated, key, val)
		}
		if !hasRows {
			fmt.Println("  (no config entries stored yet)")
		}
	}

	// Show meta
	fmt.Println()
	fmt.Println("  Schema Metadata:")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows8, err := db.Query(`
		SELECT meta_key, meta_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_META
		ORDER BY meta_key
		FETCH FIRST 5 ROWS ONLY`)
	if err == nil {
		defer rows8.Close()
		hasRows := false
		for rows8.Next() {
			hasRows = true
			var key, updated string
			var value sql.NullString
			if err := rows8.Scan(&key, &value, &updated); err != nil {
				continue
			}
			val := "(null)"
			if value.Valid {
				val = value.String
			}
			fmt.Printf("  %s  %-30s = %s\n", updated, key, val)
		}
		if !hasRows {
			fmt.Println("  (no metadata yet)")
		}
	}

	fmt.Println()
	fmt.Println("  Tip: Run 'picooraclaw oracle-inspect <table>' for details")
	fmt.Println("       Run 'picooraclaw oracle-inspect memories -s \"query\"' for semantic search")
	fmt.Println()
}

// inspectMemories shows detailed memory entries.
func inspectMemories(db *sql.DB, agentID string, limit int, searchQuery string, oracleCfg *config.OracleDBConfig) {
	fmt.Println()
	if searchQuery != "" {
		fmt.Printf("  Semantic Search: \"%s\"\n", searchQuery)
		fmt.Println("  ─────────────────────────────────────────────────────────")

		sqlQuery := fmt.Sprintf(`
			SELECT memory_id, content, importance, category,
			       ROUND(1 - VECTOR_DISTANCE(embedding,
			         VECTOR_EMBEDDING(%s USING :1 AS DATA), COSINE), 3) AS similarity,
			       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created,
			       access_count
			FROM PICO_MEMORIES
			WHERE agent_id = :2 AND embedding IS NOT NULL
			ORDER BY VECTOR_DISTANCE(embedding,
			  VECTOR_EMBEDDING(%s USING :3 AS DATA), COSINE) ASC
			FETCH FIRST :4 ROWS ONLY`,
			oracleCfg.ONNXModel, oracleCfg.ONNXModel)

		rows, err := db.Query(sqlQuery, searchQuery, agentID, searchQuery, limit)
		if err != nil {
			fmt.Printf("  Search error: %v\n", err)
			return
		}
		defer rows.Close()

		hasRows := false
		for rows.Next() {
			hasRows = true
			var memID, created string
			var content, category sql.NullString
			var importance, similarity float64
			var accessCount int
			if err := rows.Scan(&memID, &content, &importance, &category, &similarity, &created, &accessCount); err != nil {
				continue
			}
			text := "(empty)"
			if content.Valid {
				text = content.String
			}
			cat := ""
			if category.Valid && category.String != "" {
				cat = category.String
			}
			pct := similarity * 100
			fmt.Printf("\n  [%5.1f%% match]  ID: %s\n", pct, memID)
			fmt.Printf("  Created: %s  Importance: %.1f  Category: %s  Accessed: %dx\n",
				created, importance, cat, accessCount)
			fmt.Printf("  Content: %s\n", text)
		}
		if !hasRows {
			fmt.Println("  No matching memories found.")
		}
	} else {
		fmt.Println("  All Memories")
		fmt.Println("  ─────────────────────────────────────────────────────────")

		rows, err := db.Query(`
			SELECT memory_id, content, importance, category,
			       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created,
			       access_count,
			       CASE WHEN embedding IS NOT NULL THEN 'yes' ELSE 'no' END AS has_vec
			FROM PICO_MEMORIES
			WHERE agent_id = :1
			ORDER BY created_at DESC
			FETCH FIRST :2 ROWS ONLY`, agentID, limit)
		if err != nil {
			fmt.Printf("  Query error: %v\n", err)
			return
		}
		defer rows.Close()

		hasRows := false
		for rows.Next() {
			hasRows = true
			var memID, created, hasVec string
			var content, category sql.NullString
			var importance float64
			var accessCount int
			if err := rows.Scan(&memID, &content, &importance, &category, &created, &accessCount, &hasVec); err != nil {
				continue
			}
			text := "(empty)"
			if content.Valid {
				text = content.String
			}
			cat := ""
			if category.Valid && category.String != "" {
				cat = category.String
			}
			fmt.Printf("\n  ID: %s  Vector: %s\n", memID, hasVec)
			fmt.Printf("  Created: %s  Importance: %.1f  Category: %s  Accessed: %dx\n",
				created, importance, cat, accessCount)
			fmt.Printf("  Content: %s\n", text)
		}
		if !hasRows {
			fmt.Println("  No memories stored yet.")
		}
	}
	fmt.Println()
}

// inspectSessions shows stored chat sessions.
func inspectSessions(db *sql.DB, agentID string, limit int) {
	fmt.Println()
	fmt.Println("  Chat Sessions")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT session_key, summary,
		       DBMS_LOB.GETLENGTH(messages) AS msg_len,
		       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_SESSIONS
		WHERE agent_id = :1
		ORDER BY updated_at DESC
		FETCH FIRST :2 ROWS ONLY`, agentID, limit)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var sessionKey, created, updated string
		var summary sql.NullString
		var msgLen sql.NullInt64
		if err := rows.Scan(&sessionKey, &summary, &msgLen, &created, &updated); err != nil {
			continue
		}
		size := int64(0)
		if msgLen.Valid {
			size = msgLen.Int64
		}
		fmt.Printf("\n  Session: %s\n", sessionKey)
		fmt.Printf("  Created: %s  Updated: %s  Messages size: %d bytes\n", created, updated, size)
		if summary.Valid && summary.String != "" {
			fmt.Printf("  Summary: %s\n", summary.String)
		}
	}
	if !hasRows {
		fmt.Println("  No sessions stored yet.")
	}
	fmt.Println()
}

// inspectTranscripts shows conversation transcript entries.
func inspectTranscripts(db *sql.DB, agentID string, limit int) {
	fmt.Println()
	fmt.Println("  Conversation Transcripts")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT session_key, sequence_num, role, content,
		       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created
		FROM PICO_TRANSCRIPTS
		WHERE agent_id = :1
		ORDER BY id DESC
		FETCH FIRST :2 ROWS ONLY`, agentID, limit)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var role, created string
		var sessionKey sql.NullString
		var seqNum sql.NullInt64
		var content sql.NullString
		if err := rows.Scan(&sessionKey, &seqNum, &role, &content, &created); err != nil {
			continue
		}
		sess := ""
		if sessionKey.Valid {
			sess = sessionKey.String
		}
		text := "(empty)"
		if content.Valid {
			text = content.String
		}
		seq := int64(0)
		if seqNum.Valid {
			seq = seqNum.Int64
		}
		fmt.Printf("  %s  #%d  %-10s  [%s]  %s\n", created, seq, role, sess, text)
	}
	if !hasRows {
		fmt.Println("  No transcripts yet.")
	}
	fmt.Println()
}

// inspectState shows key-value state entries.
func inspectState(db *sql.DB, agentID string) {
	fmt.Println()
	fmt.Println("  Agent State (Key-Value)")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT state_key, state_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_STATE
		WHERE agent_id = :1
		ORDER BY state_key`, agentID)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var key, updated string
		var value sql.NullString
		if err := rows.Scan(&key, &value, &updated); err != nil {
			continue
		}
		val := "(null)"
		if value.Valid {
			val = value.String
		}
		fmt.Printf("  %-30s = %-40s  (%s)\n", key, val, updated)
	}
	if !hasRows {
		fmt.Println("  No state entries yet.")
	}
	fmt.Println()
}

// inspectDailyNotes shows daily note entries.
func inspectDailyNotes(db *sql.DB, agentID string, limit int) {
	fmt.Println()
	fmt.Println("  Daily Notes")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT note_id, TO_CHAR(note_date, 'YYYY-MM-DD') AS note_day, content,
		       CASE WHEN embedding IS NOT NULL THEN 'yes' ELSE 'no' END AS has_vec,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_DAILY_NOTES
		WHERE agent_id = :1
		ORDER BY note_date DESC
		FETCH FIRST :2 ROWS ONLY`, agentID, limit)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var noteID, noteDay, hasVec, updated string
		var content sql.NullString
		if err := rows.Scan(&noteID, &noteDay, &content, &hasVec, &updated); err != nil {
			continue
		}
		text := "(empty)"
		if content.Valid {
			text = content.String
		}
		fmt.Printf("\n  Date: %s  ID: %s  Vector: %s  Updated: %s\n", noteDay, noteID, hasVec, updated)
		fmt.Printf("  Content: %s\n", text)
	}
	if !hasRows {
		fmt.Println("  No daily notes yet.")
	}
	fmt.Println()
}

// inspectPrompts shows system prompts stored in Oracle.
// If nameFilter is non-empty, prints full content of that prompt only.
// If nameFilter is empty, lists all prompts with their sizes.
func inspectPrompts(db *sql.DB, agentID string, nameFilter ...string) {
	fmt.Println()

	// Single prompt: show full content.
	if len(nameFilter) > 0 && nameFilter[0] != "" {
		name := nameFilter[0]
		fmt.Printf("  Prompt: %s\n", name)
		fmt.Println("  ─────────────────────────────────────────────────────────")
		var content sql.NullString
		var updated string
		err := db.QueryRow(`
			SELECT content, TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
			FROM PICO_PROMPTS
			WHERE agent_id = :1 AND UPPER(prompt_name) = UPPER(:2)`,
			agentID, name).Scan(&content, &updated)
		if err != nil {
			fmt.Printf("  Not found: %v\n", err)
			fmt.Println()
			return
		}
		fmt.Printf("  Updated: %s\n\n", updated)
		if content.Valid {
			fmt.Println(content.String)
		} else {
			fmt.Println("  (empty)")
		}
		fmt.Println()
		return
	}

	// List view: show all prompts with size.
	fmt.Println("  System Prompts")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	fmt.Println("  (use: oracle-inspect prompts <name>  to view full content)")
	fmt.Println()

	rows, err := db.Query(`
		SELECT prompt_name, DBMS_LOB.GETLENGTH(content) AS content_len,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_PROMPTS
		WHERE agent_id = :1
		ORDER BY prompt_name`, agentID)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var name, updated string
		var contentLen sql.NullInt64
		if err := rows.Scan(&name, &contentLen, &updated); err != nil {
			continue
		}
		size := int64(0)
		if contentLen.Valid {
			size = contentLen.Int64
		}
		fmt.Printf("  %-25s  %5d chars  (%s)\n", name, size, updated)
	}
	if !hasRows {
		fmt.Println("  No prompts stored yet.")
	}
	fmt.Println()
}

// inspectConfig shows runtime config stored in Oracle.
func inspectConfig(db *sql.DB, agentID string) {
	fmt.Println()
	fmt.Println("  Stored Config")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT config_key, config_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_CONFIG
		WHERE agent_id = :1
		ORDER BY config_key`, agentID)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var key, updated string
		var value sql.NullString
		if err := rows.Scan(&key, &value, &updated); err != nil {
			continue
		}
		val := "(null)"
		if value.Valid {
			val = value.String
		}
		fmt.Printf("  %-30s = %-40s  (%s)\n", key, val, updated)
	}
	if !hasRows {
		fmt.Println("  No config entries stored yet.")
	}
	fmt.Println()
}

// inspectMeta shows schema metadata.
func inspectMeta(db *sql.DB) {
	fmt.Println()
	fmt.Println("  Schema Metadata")
	fmt.Println("  ─────────────────────────────────────────────────────────")

	rows, err := db.Query(`
		SELECT meta_key, meta_value,
		       TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI') AS updated
		FROM PICO_META
		ORDER BY meta_key`)
	if err != nil {
		fmt.Printf("  Query error: %v\n", err)
		return
	}
	defer rows.Close()

	hasRows := false
	for rows.Next() {
		hasRows = true
		var key, updated string
		var value sql.NullString
		if err := rows.Scan(&key, &value, &updated); err != nil {
			continue
		}
		val := "(null)"
		if value.Valid {
			val = value.String
		}
		fmt.Printf("  %-30s = %-30s  (%s)\n", key, val, updated)
	}
	if !hasRows {
		fmt.Println("  No metadata entries yet.")
	}

	// Also show ONNX model info
	fmt.Println()
	fmt.Println("  ONNX Models")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows2, err := db.Query(`SELECT model_name, mining_function, algorithm FROM user_mining_models ORDER BY model_name`)
	if err == nil {
		defer rows2.Close()
		hasModels := false
		for rows2.Next() {
			hasModels = true
			var modelName, miningFunc, algo string
			if err := rows2.Scan(&modelName, &miningFunc, &algo); err != nil {
				continue
			}
			fmt.Printf("  %-25s  %-15s  %s\n", modelName, miningFunc, algo)
		}
		if !hasModels {
			fmt.Println("  No ONNX models loaded.")
		}
	}

	// Show vector indexes
	fmt.Println()
	fmt.Println("  Vector Indexes")
	fmt.Println("  ─────────────────────────────────────────────────────────")
	rows3, err := db.Query(`SELECT index_name, table_name FROM user_indexes WHERE index_name LIKE 'IDX_PICO_%VEC' ORDER BY index_name`)
	if err == nil {
		defer rows3.Close()
		hasIdx := false
		for rows3.Next() {
			hasIdx = true
			var idxName, tableName string
			if err := rows3.Scan(&idxName, &tableName); err != nil {
				continue
			}
			fmt.Printf("  %-30s  on %s\n", idxName, tableName)
		}
		if !hasIdx {
			fmt.Println("  No vector indexes found.")
		}
	}
	fmt.Println()
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// webSessionAdapter satisfies web.SessionLister with a minimal in-memory stub.
// The gateway has no first-class session catalog yet; ListSessions returns
// empty, CreateSession mints an ID, and DeleteSession is a no-op. Actual
// message history still flows through the bus/agent loop.
type webSessionAdapter struct{}

func (a *webSessionAdapter) ListSessions() []web.SessionInfo { return []web.SessionInfo{} }

func (a *webSessionAdapter) CreateSession(title string) (web.SessionInfo, error) {
	return web.SessionInfo{
		ID:     fmt.Sprintf("s_%d", time.Now().UnixNano()),
		Title:  title,
		LastAt: time.Now().Unix(),
	}, nil
}

func (a *webSessionAdapter) DeleteSession(id string) error { return nil }

// webMemoryAdapter satisfies web.MemorySearcher by delegating to the Oracle
// memory store's vector Recall. Returns nil on query errors so /v1/memory
// responds with an empty array rather than a 5xx.
type webMemoryAdapter struct {
	m *oracledb.MemoryStore
}

func (a *webMemoryAdapter) Search(q string, n int) []web.MemoryResult {
	if a == nil || a.m == nil {
		return nil
	}
	recs, err := a.m.Recall(q, n)
	if err != nil {
		logger.WarnCF("web", "memory search failed", map[string]interface{}{"error": err.Error()})
		return nil
	}
	out := make([]web.MemoryResult, 0, len(recs))
	for _, r := range recs {
		out = append(out, web.MemoryResult{
			ID:    r.MemoryID,
			Text:  r.Text,
			Score: r.Score,
		})
	}
	return out
}
