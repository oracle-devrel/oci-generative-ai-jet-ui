#!/usr/bin/env python3
"""
Unified Application Launcher for Agentic RAG System.

This script provides a single entry point to launch the various
components of the Agentic RAG system:

- FastAPI Backend (always started, port 8000)
- Gradio UI (port 7860)
- Open WebUI (port 3000)

Usage:
    python run_app.py              # Both UIs (default)
    python run_app.py --gradio     # Gradio only
    python run_app.py --openwebui  # Open WebUI only
    python run_app.py --api-only   # Backend API only

Examples:
    # Start everything (default behavior)
    python run_app.py

    # Start only Open WebUI frontend
    python run_app.py --openwebui

    # Start only Gradio frontend
    python run_app.py --gradio

    # Start backend API only (for external frontends)
    python run_app.py --api-only
"""

import os
import sys
import time
import signal
import argparse
import threading
import multiprocessing
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.dirname(__file__))


def start_fastapi_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI backend server."""
    import uvicorn
    from src.main import app

    print(f"\n🚀 Starting FastAPI Backend on http://{host}:{port}")
    print(f"   📚 API Docs: http://{host}:{port}/docs")
    print(f"   🤖 OpenAI-compatible API: http://{host}:{port}/v1")

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    server.run()


def start_gradio_ui(host: str = "0.0.0.0", port: int = 7860):
    """Start the Gradio UI."""
    import traceback

    try:
        # Import here to avoid loading Gradio unnecessarily
        from gradio_app import create_interface

        print(f"\n🎨 Starting Gradio UI on http://{host}:{port}")

        interface = create_interface()
        interface.launch(
            server_name=host,
            server_port=port,
            share=False,  # Don't create public link in unified mode
            inbrowser=False,  # Don't auto-open browser
            quiet=True
        )
    except Exception as e:
        print(f"\n❌ Gradio UI failed to start: {e}")
        traceback.print_exc()
        # Keep the process alive with error state rather than exiting
        # This prevents the restart loop
        import time
        while True:
            time.sleep(60)


def start_openwebui(backend_url: str = "http://localhost:8000", port: int = 3000):
    """Start Open WebUI."""
    from openwebui_app import start_openwebui as launch_openwebui, check_open_webui_installed

    if not check_open_webui_installed():
        print("\n⚠️  Open WebUI is not installed. Installing now...")
        from openwebui_app import install_open_webui
        if not install_open_webui():
            print("❌ Failed to install Open WebUI. Skipping...")
            return

    print(f"\n🌐 Starting Open WebUI on http://0.0.0.0:{port}")

    process = launch_openwebui(
        backend_url=backend_url,
        port=port,
        host="0.0.0.0"
    )

    # Stream output
    try:
        for line in process.stdout:
            print(f"[OpenWebUI] {line}", end="")
    except Exception:
        pass


def wait_for_backend(url: str, timeout: int = 30) -> bool:
    """Wait for backend to be ready."""
    import requests

    print(f"\n⏳ Waiting for backend at {url}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/v1/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Backend is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        print(".", end="", flush=True)

    print(f"\n❌ Backend did not start within {timeout} seconds")
    return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified launcher for Agentic RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_app.py              # Start all UIs (default)
  python run_app.py --gradio     # Start Gradio UI only
  python run_app.py --openwebui  # Start Open WebUI only
  python run_app.py --api-only   # Start backend API only

Ports:
  FastAPI Backend: 8000
  Gradio UI:       7860
  Open WebUI:      3000
        """
    )

    # UI selection (mutually exclusive group for specific modes)
    ui_group = parser.add_mutually_exclusive_group()
    ui_group.add_argument(
        "--gradio",
        action="store_true",
        help="Start Gradio UI only (with backend)"
    )
    ui_group.add_argument(
        "--openwebui",
        action="store_true",
        help="Start Open WebUI only (with backend)"
    )
    ui_group.add_argument(
        "--api-only",
        action="store_true",
        help="Start backend API only (no UI)"
    )

    # Port configuration
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="Port for FastAPI backend (default: 8000)"
    )
    parser.add_argument(
        "--gradio-port",
        type=int,
        default=7860,
        help="Port for Gradio UI (default: 7860)"
    )
    parser.add_argument(
        "--openwebui-port",
        type=int,
        default=3000,
        help="Port for Open WebUI (default: 3000)"
    )

    # Host configuration
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    # Determine which components to start
    start_gradio = not args.openwebui and not args.api_only
    start_open_webui = not args.gradio and not args.api_only

    # If specific UI requested, only start that one
    if args.gradio:
        start_gradio = True
        start_open_webui = False
    elif args.openwebui:
        start_gradio = False
        start_open_webui = True

    print("\n" + "=" * 60)
    print("🤖 Agentic RAG System - Unified Launcher")
    print("=" * 60)
    print(f"\nComponents to start:")
    print(f"  ✅ FastAPI Backend (port {args.api_port})")
    if start_gradio:
        print(f"  ✅ Gradio UI (port {args.gradio_port})")
    else:
        print(f"  ⏭️  Gradio UI (skipped)")
    if start_open_webui:
        print(f"  ✅ Open WebUI (port {args.openwebui_port})")
    else:
        print(f"  ⏭️  Open WebUI (skipped)")
    print("=" * 60)

    processes: List[multiprocessing.Process] = []

    # Start FastAPI backend in a separate process
    backend_process = multiprocessing.Process(
        target=start_fastapi_server,
        args=(args.host, args.api_port),
        name="FastAPI-Backend"
    )
    backend_process.start()
    processes.append(backend_process)

    # Wait for backend to be ready before starting frontends
    backend_url = f"http://localhost:{args.api_port}"
    time.sleep(2)  # Give it a moment to start

    if not wait_for_backend(backend_url, timeout=60):
        print("❌ Backend failed to start. Exiting...")
        for p in processes:
            p.terminate()
        sys.exit(1)

    # Start Gradio if requested
    if start_gradio:
        gradio_process = multiprocessing.Process(
            target=start_gradio_ui,
            args=(args.host, args.gradio_port),
            name="Gradio-UI"
        )
        gradio_process.start()
        processes.append(gradio_process)

    # Start Open WebUI if requested
    if start_open_webui:
        openwebui_process = multiprocessing.Process(
            target=start_openwebui,
            args=(backend_url, args.openwebui_port),
            name="Open-WebUI"
        )
        openwebui_process.start()
        processes.append(openwebui_process)

    # Print access URLs
    time.sleep(3)
    print("\n" + "=" * 60)
    print("🎉 All components started successfully!")
    print("=" * 60)
    print(f"\n📡 FastAPI Backend:")
    print(f"   API: http://{args.host}:{args.api_port}")
    print(f"   Docs: http://{args.host}:{args.api_port}/docs")
    print(f"   OpenAI API: http://{args.host}:{args.api_port}/v1")
    if start_gradio:
        print(f"\n🎨 Gradio UI:")
        print(f"   http://{args.host}:{args.gradio_port}")
    if start_open_webui:
        print(f"\n🌐 Open WebUI:")
        print(f"   http://{args.host}:{args.openwebui_port}")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop all services")
    print("=" * 60 + "\n")

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down all services...")
        for p in processes:
            if p.is_alive():
                print(f"   Stopping {p.name}...")
                p.terminate()
                p.join(timeout=5)
                if p.is_alive():
                    p.kill()
        print("✅ All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep main process alive and monitor children
    # Track which processes have been reported as stopped
    stopped_processes = set()
    try:
        while True:
            for p in processes:
                if not p.is_alive() and p.name not in stopped_processes:
                    print(f"⚠️  {p.name} has stopped unexpectedly (exit code: {p.exitcode})")
                    stopped_processes.add(p.name)
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    # Set multiprocessing start method for compatibility
    multiprocessing.set_start_method("spawn", force=True)
    main()
