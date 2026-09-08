package server

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
)

const (
	ServerPort    = 8080
	ServerHost    = "localhost"
	StartTimeout  = 10 * time.Second
	StopTimeout   = 3 * time.Second
	HealthCheckInterval = 200 * time.Millisecond
)

// Manager handles the lifecycle of server.py
type Manager struct {
	cmd        *exec.Cmd
	projectDir string
	running    bool
}

// NewManager creates a new server manager
func NewManager(projectDir string) *Manager {
	return &Manager{
		projectDir: projectDir,
		running:    false,
	}
}

// IsPortInUse checks if the server port is already in use
func (m *Manager) IsPortInUse() bool {
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", ServerHost, ServerPort), time.Second)
	if err != nil {
		return false
	}
	conn.Close()
	return true
}

// IsHealthy checks if the server is responding
func (m *Manager) IsHealthy() bool {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(fmt.Sprintf("http://%s:%d/api/tags", ServerHost, ServerPort))
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// Start launches server.py as a subprocess
func (m *Manager) Start() error {
	// Check if already running
	if m.IsPortInUse() {
		if m.IsHealthy() {
			m.running = true
			return nil // Server already running, reuse it
		}
		return fmt.Errorf("port %d is in use but server is not healthy", ServerPort)
	}

	// Find server.py path
	serverPath := filepath.Join(m.projectDir, "server.py")
	if _, err := os.Stat(serverPath); os.IsNotExist(err) {
		return fmt.Errorf("server.py not found at %s", serverPath)
	}

	// Start the server
	m.cmd = exec.Command("python", serverPath)
	m.cmd.Dir = m.projectDir

	// Redirect stderr to see any startup errors
	m.cmd.Stderr = os.Stderr

	// Start in a new process group so we can kill it cleanly
	m.cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err := m.cmd.Start(); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}

	// Wait for server to become healthy
	deadline := time.Now().Add(StartTimeout)
	for time.Now().Before(deadline) {
		if m.IsHealthy() {
			m.running = true
			return nil
		}
		time.Sleep(HealthCheckInterval)
	}

	// Timeout - kill the server and return error
	m.Stop()
	return fmt.Errorf("server failed to start within %v", StartTimeout)
}

// Stop gracefully shuts down the server
func (m *Manager) Stop() error {
	if m.cmd == nil || m.cmd.Process == nil {
		m.running = false
		return nil
	}

	// Send SIGTERM to the process group
	pgid, err := syscall.Getpgid(m.cmd.Process.Pid)
	if err == nil {
		syscall.Kill(-pgid, syscall.SIGTERM)
	} else {
		m.cmd.Process.Signal(syscall.SIGTERM)
	}

	// Wait for graceful shutdown with timeout
	done := make(chan error, 1)
	go func() {
		done <- m.cmd.Wait()
	}()

	select {
	case <-done:
		// Graceful shutdown succeeded
	case <-time.After(StopTimeout):
		// Force kill
		if pgid, err := syscall.Getpgid(m.cmd.Process.Pid); err == nil {
			syscall.Kill(-pgid, syscall.SIGKILL)
		} else {
			m.cmd.Process.Kill()
		}
	}

	m.running = false
	m.cmd = nil
	return nil
}

// IsRunning returns whether the server is running
func (m *Manager) IsRunning() bool {
	return m.running && m.IsHealthy()
}

// GetURL returns the server URL
func (m *Manager) GetURL() string {
	return fmt.Sprintf("http://%s:%d", ServerHost, ServerPort)
}
