package oracle

import (
	"testing"

	"github.com/jasperan/picooraclaw/pkg/config"
)

func TestBuildConnStr_FreePDB(t *testing.T) {
	cfg := &config.OracleDBConfig{
		Mode:     "freepdb",
		Host:     "localhost",
		Port:     1521,
		Service:  "FREEPDB1",
		User:     "picooraclaw",
		Password: "test123",
	}

	connStr := BuildConnStr(cfg)
	if connStr == "" {
		t.Fatal("expected non-empty connection string for FreePDB mode")
	}
	// go-ora BuildUrl returns an oracle:// URL
	if len(connStr) < 10 {
		t.Errorf("connection string too short: %q", connStr)
	}
}

func TestBuildConnStr_ADB_DSN(t *testing.T) {
	dsn := "tcps://adb.region.oraclecloud.com:1522/abc_high.adb.oraclecloud.com"
	cfg := &config.OracleDBConfig{
		Mode: "adb",
		DSN:  dsn,
	}

	connStr := BuildConnStr(cfg)
	if connStr != dsn {
		t.Errorf("expected DSN passthrough, got %q", connStr)
	}
}

func TestBuildConnStr_ADB_Wallet(t *testing.T) {
	cfg := &config.OracleDBConfig{
		Mode:       "adb",
		Host:       "adb.region.oraclecloud.com",
		Port:       1522,
		Service:    "svc_high",
		User:       "admin",
		Password:   "pass",
		WalletPath: "/path/to/wallet",
	}

	connStr := BuildConnStr(cfg)
	if connStr == "" {
		t.Fatal("expected non-empty connection string for ADB wallet mode")
	}
}

func TestOracleDBConfig_Modes(t *testing.T) {
	tests := []struct {
		name       string
		cfg        config.OracleDBConfig
		isADB      bool
		usesWallet bool
		usesTLS    bool
	}{
		{
			name:       "FreePDB default",
			cfg:        config.OracleDBConfig{Mode: "freepdb"},
			isADB:      false,
			usesWallet: false,
			usesTLS:    false,
		},
		{
			name:       "ADB with wallet",
			cfg:        config.OracleDBConfig{Mode: "adb", WalletPath: "/wallet"},
			isADB:      true,
			usesWallet: true,
			usesTLS:    false,
		},
		{
			name:       "ADB with DSN (wallet-less TLS)",
			cfg:        config.OracleDBConfig{Mode: "adb", DSN: "tcps://..."},
			isADB:      true,
			usesWallet: false,
			usesTLS:    true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.cfg.IsADB(); got != tt.isADB {
				t.Errorf("IsADB() = %v, want %v", got, tt.isADB)
			}
			if got := tt.cfg.UsesWallet(); got != tt.usesWallet {
				t.Errorf("UsesWallet() = %v, want %v", got, tt.usesWallet)
			}
			if got := tt.cfg.UsesTLS(); got != tt.usesTLS {
				t.Errorf("UsesTLS() = %v, want %v", got, tt.usesTLS)
			}
		})
	}
}
