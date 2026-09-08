"""
Open WebUI Launcher for Agentic RAG System.

This module configures and launches Open WebUI to connect to our
FastAPI backend's OpenAI-compatible API endpoints.

Open WebUI will see our reasoning strategies as "models" and can
interact with them through the standard OpenAI chat interface.

Usage:
    python openwebui_app.py

Or use the unified launcher:
    python run_app.py --openwebui
"""

import os
import sys
import subprocess
import shutil
import time
from typing import Optional


def check_open_webui_installed() -> bool:
    """Check if Open WebUI is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "open-webui"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def install_open_webui():
    """Install Open WebUI via pip."""
    print("Installing Open WebUI...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "open-webui"],
            check=True
        )
        print("✅ Open WebUI installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Open WebUI: {e}")
        return False


def find_open_webui_command() -> Optional[str]:
    """Find the open-webui command."""
    # Check if open-webui is in PATH
    open_webui_path = shutil.which("open-webui")
    if open_webui_path:
        return open_webui_path

    # Check common locations
    possible_paths = [
        os.path.expanduser("~/.local/bin/open-webui"),
        "/usr/local/bin/open-webui",
        os.path.join(sys.prefix, "bin", "open-webui"),
    ]

    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


def start_openwebui(
    backend_url: str = "http://localhost:8000",
    port: int = 3000,
    host: str = "0.0.0.0",
    data_dir: Optional[str] = None
) -> subprocess.Popen:
    """
    Launch Open WebUI configured to use our backend.

    Args:
        backend_url: URL of the FastAPI backend with OpenAI-compatible API
        port: Port for Open WebUI (default: 3000)
        host: Host to bind to (default: 0.0.0.0)
        data_dir: Directory for Open WebUI data (default: ./openwebui_data)

    Returns:
        subprocess.Popen: The Open WebUI process
    """
    # Set up environment variables
    env = os.environ.copy()

    # OpenAI-compatible API configuration
    env["OPENAI_API_BASE_URL"] = f"{backend_url}/v1"
    env["OPENAI_API_BASE_URLS"] = f"{backend_url}/v1"
    env["OPENAI_API_KEY"] = "not-needed"  # Our backend doesn't require auth
    env["OPENAI_API_KEYS"] = "not-needed"

    # Disable default Ollama integration (we provide our own models)
    env["ENABLE_OLLAMA_API"] = "false"
    env["OLLAMA_BASE_URL"] = ""

    # Server configuration
    env["PORT"] = str(port)
    env["HOST"] = host

    # Authentication (disabled for local development)
    env["WEBUI_AUTH"] = "false"
    env["WEBUI_AUTH_TRUSTED_EMAIL_HEADER"] = ""

    # Data directory
    if data_dir:
        env["DATA_DIR"] = data_dir
    else:
        env["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "openwebui_data")

    # Create data directory if it doesn't exist
    os.makedirs(env["DATA_DIR"], exist_ok=True)

    # Additional settings
    env["ENABLE_SIGNUP"] = "true"
    env["DEFAULT_USER_ROLE"] = "admin"
    env["WEBUI_NAME"] = "Agentic RAG - Open WebUI"
    env["ENABLE_COMMUNITY_SHARING"] = "false"

    # Find the open-webui command
    open_webui_cmd = find_open_webui_command()

    if not open_webui_cmd:
        # Try running as a module
        print("Running Open WebUI as Python module...")
        cmd = [sys.executable, "-m", "open_webui.main", "--host", host, "--port", str(port)]
    else:
        cmd = [open_webui_cmd, "serve", "--host", host, "--port", str(port)]

    print(f"\n{'='*60}")
    print("🌐 Starting Open WebUI")
    print(f"{'='*60}")
    print(f"📡 Backend API: {backend_url}/v1")
    print(f"🖥️  Open WebUI URL: http://{host}:{port}")
    print(f"📁 Data Directory: {env['DATA_DIR']}")
    print(f"{'='*60}\n")

    # Start Open WebUI
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    return process


def main():
    """Main entry point for Open WebUI launcher."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Open WebUI connected to Agentic RAG backend"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="URL of the FastAPI backend (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for Open WebUI (default: 3000)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Directory for Open WebUI data"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install Open WebUI if not present"
    )

    args = parser.parse_args()

    # Check if Open WebUI is installed
    if not check_open_webui_installed():
        if args.install:
            if not install_open_webui():
                sys.exit(1)
        else:
            print("❌ Open WebUI is not installed.")
            print("Run with --install flag or install manually:")
            print("    pip install open-webui")
            sys.exit(1)

    # Start Open WebUI
    process = start_openwebui(
        backend_url=args.backend_url,
        port=args.port,
        host=args.host,
        data_dir=args.data_dir
    )

    try:
        # Stream output
        for line in process.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Open WebUI...")
        process.terminate()
        process.wait(timeout=10)
        print("✅ Open WebUI stopped.")


if __name__ == "__main__":
    main()
