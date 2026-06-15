"""Build the self-contained interactive 3D viewer (one HTML file) and serve it locally.

The viewer is `viewer/template.html` with the scene JSON injected at the `/*SCENE_JSON*/` marker. three.js
is loaded from a CDN (needs internet at view time). ES-module pages can't load from file://, so we serve
the file over a tiny localhost HTTP server and open the browser.
"""
from __future__ import annotations

import json
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PLACEHOLDER = "/*SCENE_JSON*/"


def build_viewer_html(scene: dict, template_path: Path) -> str:
    tmpl = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in tmpl:
        raise ValueError(f"viewer template {template_path} is missing the {PLACEHOLDER} marker")
    return tmpl.replace(PLACEHOLDER, json.dumps(scene))


def serve_and_open(directory: Path, filename: str, port: int | None = None) -> None:
    """Serve `directory` on localhost and open `filename` in the browser. Blocks until Ctrl-C."""
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", port or 0), handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/{filename}"
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print(f"  viewer at {url}")
    print("  (opening browser… press Ctrl-C here to stop the server)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  viewer stopped.")
    finally:
        httpd.server_close()
