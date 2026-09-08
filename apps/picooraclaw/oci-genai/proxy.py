#!/usr/bin/env python3
"""OCI GenAI local proxy -- OpenAI-compatible endpoint backed by OCI GenAI.

Starts a threaded local server that accepts standard OpenAI API calls
(including streaming) and forwards them to OCI GenAI using OCI
authentication from ~/.oci/config.

Prerequisites:
    pip install -r requirements.txt
    # Configure ~/.oci/config with your OCI credentials

Usage:
    python proxy.py                          # starts on port 9999
    OCI_PROXY_PORT=8888 python proxy.py      # custom port

Then configure PicoOraClaw with:
    "provider": "openai",
    "api_base": "http://localhost:9999/v1",
    "api_key": "oci-genai",
    "model": "meta.llama-3.3-70b-instruct"
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from oci_client import create_oci_client

PROXY_PORT = int(os.getenv("OCI_PROXY_PORT", "9999"))


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle each request in a separate thread."""

    daemon_threads = True


class OCIProxyHandler(BaseHTTPRequestHandler):
    client = None

    # ── CORS ────────────────────────────────────────────────────
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, Authorization"
        )

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ── POST /v1/chat/completions ───────────────────────────────
    def do_POST(self):
        if "/chat/completions" not in self.path:
            return self._json(404, {"error": {"message": "Not found"}})

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))
        stream = body.get("stream", False)

        try:
            if stream:
                self._handle_stream(body)
            else:
                response = self.client.chat.completions.create(**body)
                self._json(200, response.model_dump())
        except Exception as exc:
            self._json(
                500,
                {"error": {"message": str(exc), "type": "oci_genai_error"}},
            )

    def _handle_stream(self, body):
        """Forward a streaming chat-completion as Server-Sent Events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors_headers()
        self.end_headers()
        try:
            for chunk in self.client.chat.completions.create(**body):
                data = json.dumps(chunk.model_dump())
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as exc:
            err = json.dumps(
                {"error": {"message": str(exc), "type": "oci_genai_error"}}
            )
            self.wfile.write(f"data: {err}\n\n".encode())
            self.wfile.flush()

    # ── GET endpoints ───────────────────────────────────────────
    def do_GET(self):
        if "/models" in self.path:
            self._json(200, {"object": "list", "data": []})
        elif "/health" in self.path:
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": {"message": "Not found"}})

    # ── Helpers ─────────────────────────────────────────────────
    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args):  # noqa: ARG002
        sys.stderr.write(f"[oci-proxy] {args[0]}\n")


# ── Main ────────────────────────────────────────────────────────
def main():
    if not os.getenv("OCI_COMPARTMENT_ID"):
        print("ERROR: OCI_COMPARTMENT_ID environment variable is required.")
        print("Set it to your OCI compartment OCID.")
        sys.exit(1)

    client = create_oci_client()
    OCIProxyHandler.client = client

    server = ThreadedHTTPServer(("0.0.0.0", PROXY_PORT), OCIProxyHandler)
    print(f"OCI GenAI proxy listening on http://localhost:{PROXY_PORT}/v1")
    print(f"  Region:      {os.getenv('OCI_REGION', 'us-chicago-1')}")
    print(f"  Profile:     {os.getenv('OCI_PROFILE', 'DEFAULT')}")
    print(f"  Compartment: {os.getenv('OCI_COMPARTMENT_ID', '')[:50]}...")
    print()
    print("Configure PicoOraClaw with:")
    print(f'  "api_base": "http://localhost:{PROXY_PORT}/v1"')
    print(f'  "api_key": "oci-genai"')
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
