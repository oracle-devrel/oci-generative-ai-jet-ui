package oracle

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/jasperan/picooraclaw/pkg/config"
	"github.com/jasperan/picooraclaw/pkg/logger"
	go_ora "github.com/sijms/go-ora/v2"
)

// ConnectionManager wraps *sql.DB via go-ora for Oracle Database connectivity.
type ConnectionManager struct {
	db  *sql.DB
	cfg *config.OracleDBConfig
}

// NewConnectionManager creates a new ConnectionManager and establishes the pool.
func NewConnectionManager(cfg *config.OracleDBConfig) (*ConnectionManager, error) {
	connStr := BuildConnStr(cfg)

	db, err := sql.Open("oracle", connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to open Oracle connection: %w", err)
	}

	db.SetMaxOpenConns(cfg.PoolMaxOpen)
	db.SetMaxIdleConns(cfg.PoolMaxIdle)
	db.SetConnMaxLifetime(30 * time.Minute)
	db.SetConnMaxIdleTime(5 * time.Minute)

	cm := &ConnectionManager{
		db:  db,
		cfg: cfg,
	}

	if err := cm.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("Oracle ping failed: %w", err)
	}

	logger.InfoC("oracle", "Connection pool established")
	return cm, nil
}

// BuildConnStr constructs the go-ora connection string.
func BuildConnStr(cfg *config.OracleDBConfig) string {
	if cfg.IsADB() && cfg.DSN != "" {
		// ADB wallet-less TLS or full DSN
		return cfg.DSN
	}

	if cfg.IsADB() && cfg.UsesWallet() {
		// ADB with mTLS wallet
		return go_ora.BuildUrl(cfg.Host, cfg.Port, cfg.Service, cfg.User, cfg.Password,
			map[string]string{
				"WALLET": cfg.WalletPath,
			})
	}

	// FreePDB mode (default)
	return go_ora.BuildUrl(cfg.Host, cfg.Port, cfg.Service, cfg.User, cfg.Password, nil)
}

// DB returns the underlying *sql.DB.
func (cm *ConnectionManager) DB() *sql.DB {
	return cm.db
}

// Ping checks the Oracle connection.
func (cm *ConnectionManager) Ping() error {
	return cm.db.Ping()
}

// Close closes the connection pool.
func (cm *ConnectionManager) Close() error {
	logger.InfoC("oracle", "Closing connection pool")
	return cm.db.Close()
}

// WithTx executes a function within a transaction.
func (cm *ConnectionManager) WithTx(fn func(tx *sql.Tx) error) error {
	tx, err := cm.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}

	if err := fn(tx); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			return fmt.Errorf("rollback failed: %v (original error: %w)", rbErr, err)
		}
		return err
	}

	return tx.Commit()
}
