from typing import Dict, Optional
import yaml
from pathlib import Path
import oracledb

def load_config() -> Dict[str, str]:
    """Load configuration from config.yaml"""
    try:
        # Look for config.yaml in the current directory or parents
        current_dir = Path.cwd()
        config_path = current_dir / "config.yaml"
        if not config_path.exists():
            # Fallback to looking in the project root if we are in src
            config_path = current_dir.parent / "config.yaml"
            
        if not config_path.exists():
            print("Warning: config.yaml not found. Using empty configuration.")
            return {}
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config if config else {}
    except Exception as e:
        print(f"Warning: Error loading config: {str(e)}")
        return {}

def get_db_connection(config: Optional[Dict[str, str]] = None) -> oracledb.Connection:
    """Establish a connection to the Oracle Database"""
    if config is None:
        config = load_config()
        
    username = config.get("ORACLE_DB_USERNAME", "ADMIN")
    password = config.get("ORACLE_DB_PASSWORD", "")
    dsn = config.get("ORACLE_DB_DSN", "")
    wallet_path = config.get("ORACLE_DB_WALLET_LOCATION")
    wallet_password = config.get("ORACLE_DB_WALLET_PASSWORD")
    
    if not password or not dsn:
        raise ValueError("Oracle DB credentials not found in config.yaml.")
        
    try:
        if not wallet_path:
            print(f'Connecting (no wallet) to dsn {dsn} and user {username}')
            connection = oracledb.connect(user=username, password=password, dsn=dsn)
        else:
            print(f'Connecting (with wallet) to dsn {dsn} and user {username}')
            connection = oracledb.connect(user=username, password=password, dsn=dsn, 
                                       config_dir=wallet_path, wallet_location=wallet_path, wallet_password=wallet_password)
        return connection
    except Exception as e:
        print("Oracle DB Connection failed!", e)
        raise
