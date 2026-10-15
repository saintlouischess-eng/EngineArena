"""Loopback-only art preview. Serves no application APIs or tournament data."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]

class Preview(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        url = unquote(urlsplit(path).path)
        if url == '/':
            return str(ROOT / 'prototypes/live-club/index.html')
        # Only render assets and this prototype are reachable, not DBs or source secrets.
        selected = (ROOT / url.lstrip('/')).resolve()
        allowed = (ROOT / 'ui', ROOT / 'prototypes/live-club')
        if not any(selected.is_relative_to(folder) for folder in allowed):
            return str(ROOT / 'prototypes/live-club/does-not-exist')
        return str(selected)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Preview)
    print(f'http://127.0.0.1:{server.server_port}/prototypes/live-club/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
