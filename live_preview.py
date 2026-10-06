"""Tiny, dependency-free local preview server with automatic browser refresh."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os


ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("FRETBOARD_PREVIEW_PORT", "5500"))
RELOAD_SCRIPT = b"""
<script>
(() => {
  let version = null;
  setInterval(async () => {
    try {
      const response = await fetch('/__live_reload_version', { cache: 'no-store' });
      const nextVersion = await response.text();
      if (version !== null && nextVersion !== version) location.reload();
      version = nextVersion;
    } catch (_) {}
  }, 700);
})();
</script>
"""


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/__live_reload_version":
            page = ROOT / "index.html"
            try:
                version = f"{page.stat().st_mtime_ns}:{page.stat().st_size}"
            except OSError:
                version = "missing"
            body = version.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        if self.path.split("?", 1)[0] == "/" or self.path.split("?", 1)[0] == "/index.html":
            page = ROOT / "index.html"
            try:
                content = page.read_bytes()
            except OSError:
                self.send_error(404, "index.html not found")
                return None
            insertion = content.lower().rfind(b"</body>")
            if insertion >= 0:
                content = content[:insertion] + RELOAD_SCRIPT + content[insertion:]
            from io import BytesIO

            stream = BytesIO(content)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            return stream
        return super().send_head()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), PreviewHandler)
    print(f"Fret-board preview: http://127.0.0.1:{PORT}")
    print("Keep this window open. Press Ctrl+C to stop the preview.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPreview stopped.")
    finally:
        server.server_close()
