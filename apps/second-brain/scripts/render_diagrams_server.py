"""Serve ONLY the diagram assets + accept POST /save to write renders into docs/images/.
Used with render-excalidraw.html to regenerate the hand-drawn diagrams after
editing the .excalidraw sources:
  1. ./.venv/bin/python scripts/render_diagrams_server.py   (or python3)
  2. open http://127.0.0.1:8123/render-excalidraw.html
  3. wait for DONE — docs/images/*-hand.svg are rewritten

Security: this intentionally does NOT serve the repo root (which can contain
oracle/.env with real credentials). Only render-excalidraw.html and files under
docs/images/ are reachable, the Host header must be local (blocks DNS-rebinding),
and saves are restricted to .svg/.png names inside docs/images/.
"""
import http.server
import pathlib
import shutil
import urllib.parse

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "images"
PAGE = REPO / "render-excalidraw.html"

ALLOWED_HOSTS = {"127.0.0.1:8123", "localhost:8123"}
SAVE_SUFFIXES = {".svg", ".png"}


class H(http.server.BaseHTTPRequestHandler):
    def _deny(self, code, msg):
        self.send_response(code)
        self.end_headers()
        self.wfile.write(msg.encode())

    def _host_ok(self):
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def do_GET(self):
        if not self._host_ok():
            return self._deny(403, "bad host")
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/render-excalidraw.html"):
            target = PAGE
        elif path.startswith("/docs/images/"):
            target = OUT / pathlib.Path(path).name      # flatten: no traversal
        else:
            return self._deny(404, "not served")
        if not target.is_file():
            return self._deny(404, "missing")
        self.send_response(200)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        with open(target, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def do_POST(self):
        if self.headers.get("X-Render") != "1":
            self.send_error(403, "missing X-Render header (CSRF guard)")
            return
        if not self._host_ok():
            return self._deny(403, "bad host")
        q = urllib.parse.urlparse(self.path)
        if q.path != "/save":
            return self._deny(404, "not served")
        name = pathlib.Path(urllib.parse.parse_qs(q.query).get("name", ["out.svg"])[0]).name
        if pathlib.Path(name).suffix.lower() not in SAVE_SUFFIXES:
            return self._deny(400, "only .svg/.png saves allowed")
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        (OUT / name).write_bytes(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"saved")
        print(f"saved {name} ({len(body)} bytes)")


if __name__ == "__main__":
    print("http://127.0.0.1:8123/render-excalidraw.html")
    http.server.HTTPServer(("127.0.0.1", 8123), H).serve_forever()
