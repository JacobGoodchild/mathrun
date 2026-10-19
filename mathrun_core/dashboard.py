"""Local dashboard web server. Listens on 127.0.0.1 only.

Serves the static site in ``docs/``; requests for ``/status/...`` are served
from the live ``data/status/`` folder (falling back to ``docs/status/``).
"""

import functools
import http.server
import os
import threading
import webbrowser

from . import paths


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/status/"):
            name = os.path.basename(clean)
            live = os.path.join(paths.status_dir(), name)
            if os.path.exists(live):
                return live
            return os.path.join(paths.DOCS, "status", name)
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def serve(port, open_browser=True):
    handler = functools.partial(Handler, directory=paths.DOCS)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", int(port)), handler)
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("Dashboard: %s  (Ctrl-C to close; searchers keep running)" % url)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
