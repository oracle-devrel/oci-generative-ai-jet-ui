#!/usr/bin/env python3
"""
Simple Oracle connection test
"""

import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test Oracle connection with current credentials."""
    print("🔍 Testing Oracle connection...")
    print(f"   User: {os.getenv('ORACLE_USER')}")
    print(f"   DSN: {os.getenv('ORACLE_DSN')}")
    print(f"   Wallet: {os.getenv('ORACLE_WALLET_LOCATION')}")
    
    try:
        conn = oracledb.connect(
            user=os.getenv("ORACLE_USER"),
            password=os.getenv("ORACLE_PASSWORD"),
            dsn=os.getenv("ORACLE_DSN"),
            config_dir=os.getenv("ORACLE_WALLET_LOCATION"),
            wallet_location=os.getenv("ORACLE_WALLET_LOCATION")
        )
        
        print("✅ Connection successful!")
        print(f"   Database version: {conn.version}")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 'Hello from Oracle!' FROM DUAL")
        result = cursor.fetchone()
        print(f"   Test query result: {result[0]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Verify your Oracle username (usually 'ADMIN' for Autonomous DB)")
        print("   2. Check your password is correct")
        print("   3. Ensure the wallet files are properly configured")
        print("   4. Confirm the DSN matches your database service name")
        return False

if __name__ == "__main__":
    test_connection()
