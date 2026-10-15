"""
agent_server.py — HTTP server that bridges the agent environment to the live viewer.

Provides:
  GET /                          → live viewer HTML (viewer/live.html)
  GET /api/events                → SSE stream of agent progress events
  POST /api/event                → agent pushes a progress event
  GET /api/scene.glb             → current scene .glb (auto-refreshs when updated)
  GET /api/scene.json            → current scene schema
  GET /api/frames/<filename>     → rendered frames (PNGs)
  GET /api/status                → current session status JSON

Usage:
    # Start the server (runs in background, serves on port 8765)
    python3 scripts/agent_server.py --port 8765 --workdir /tmp/agent_session

    # Agent pushes events by POSTing to /api/event:
    curl -X POST http://localhost:8765/api/event \\
        -H 'Content-Type: application/json' \\
        -d '{"type":"progress","message":"Building scene...","step":1,"total":5}'

    # Agent updates the scene by copying a new .glb to workdir/scene.glb
    # The server auto-detects the file change and notifies viewers via SSE.

The viewer (viewer/live.html) connects to /api/events on load and
auto-refreshes the .glb when notified. This gives the user a live view
of the agent's work without any manual refresh.
"""
import argparse
import json
import os
import re
import sys
import threading
import time
import http.server
import socketserver
from pathlib import Path
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Thread-safe event broker (SSE)
# ---------------------------------------------------------------------------

class EventBroker:
    """In-memory pub/sub for SSE events. One queue per connected client."""

    def __init__(self):
        self._clients: List[List[Dict]] = []
        self._lock = threading.Lock()
        self._history: List[Dict] = []  # last N events for replay on connect
        self._max_history = 100

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            for q in self._clients:
                q.append(event)

    def subscribe(self) -> List[Dict]:
        q: List[Dict] = []
        with self._lock:
            # Replay history on subscribe so new clients see prior events
            q.extend(self._history)
            self._clients.append(q)
        return q

    def unsubscribe(self, q: List[Dict]) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)


broker = EventBroker()


# ---------------------------------------------------------------------------
# File watcher for scene.glb changes
# ---------------------------------------------------------------------------

def _watcher_transition(prev, announced, cur):
    """D10 (session-18): two-poll size-stability decision (pure — unit-tested
    in tests/test_s18_wave_d.py).

    The old watcher fired scene_updated the instant mtime moved — i.e.
    MID-COPY — so the viewer fetched a truncated .glb and rendered garbage.
    A change is announced only when (mtime, size) is IDENTICAL across two
    consecutive polls (~interval apart: the writer has settled) AND differs
    from what was last announced.

    Args:
        prev: (mtime, size) seen at the previous poll (None = none yet).
        announced: (mtime, size) last announced to viewers (None = nothing).
        cur: (mtime, size) seen now.

    Returns (fire: bool, new_announced).
    """
    if cur == prev and announced is not None and cur != announced:
        return True, cur
    return False, announced


class FileWatcher:
    """Watches a file and publishes an event when it stops changing
    (D10: two consecutive polls agree on mtime AND size)."""

    def __init__(self, path: str, broker: EventBroker, interval: float = 0.5):
        self.path = path
        self.broker = broker
        self.interval = interval
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self):
        # D10 (session-18): two-poll size-stability — see
        # _watcher_transition. Initial detection becomes a silent baseline
        # (viewers fetch it via initialLoad; no event fires), exactly the
        # old "don't fire on initial detection" behavior.
        prev = None
        announced = None
        while not self._stop.is_set():
            try:
                if os.path.exists(self.path):
                    cur = (os.path.getmtime(self.path),
                           os.path.getsize(self.path))
                    if announced is None:
                        announced = cur  # initial detection: baseline only
                    else:
                        fire, announced = _watcher_transition(
                            prev, announced, cur)
                        if fire:
                            self.broker.publish({
                                "type": "scene_updated",
                                "message": f"Scene .glb updated "
                                           f"({cur[1]} bytes)",
                                "timestamp": time.time(),
                                "size": cur[1],
                            })
                    prev = cur
            except Exception as e:
                print(f"[watcher] error: {e}", file=sys.stderr)
            self._stop.wait(self.interval)


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class AgentServerHandler(http.server.BaseHTTPRequestHandler):
    workdir = "/tmp/agent_session"  # set by main()
    viewer_dir = None  # set by main()

    def log_message(self, format, *args):
        # Suppress default logging (too noisy); print to stderr instead
        print(f"[server] {self.address_string()} - {format % args}", file=sys.stderr)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str, content_type: str, cache_max_age: int = 0):
        if not os.path.exists(path):
            self.send_error(404, f"Not found: {os.path.basename(path)}")
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache_max_age > 0:
            self.send_header("Cache-Control", f"max-age={cache_max_age}")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            viewer_path = os.path.join(self.viewer_dir, "live.html")
            self._send_file(viewer_path, "text/html")
            return

        if path == "/api/events":
            self._handle_sse()
            return

        if path == "/api/scene.glb":
            glb_path = os.path.join(self.workdir, "scene.glb")
            if not os.path.exists(glb_path):
                self.send_error(404, "No scene.glb yet — agent hasn't exported one")
                return
            self._send_file(glb_path, "model/gltf-binary", cache_max_age=0)
            return

        if path == "/api/scene.json":
            json_path = os.path.join(self.workdir, "scene.json")
            if not os.path.exists(json_path):
                self._send_json({"error": "No scene.json yet"}, status=404)
                return
            self._send_file(json_path, "application/json")
            return

        if path == "/api/metadata.json":
            meta_path = os.path.join(self.workdir, "metadata.json")
            if not os.path.exists(meta_path):
                self._send_json({"error": "No metadata.json yet"}, status=404)
                return
            self._send_file(meta_path, "application/json")
            return

        if path == "/api/status":
            glb_path = os.path.join(self.workdir, "scene.glb")
            self._send_json({
                "workdir": self.workdir,
                "scene_glb_exists": os.path.exists(glb_path),
                "scene_glb_size": os.path.getsize(glb_path) if os.path.exists(glb_path) else 0,
                "events_in_history": len(broker._history),
                "server_time": time.time(),
            })
            return

        if path.startswith("/api/frames/"):
            filename = os.path.basename(path)
            if not re.match(r'^[a-zA-Z0-9_\-\.]+\.png$', filename):
                self.send_error(400, "Invalid filename")
                return
            frame_path = os.path.join(self.workdir, "frames", filename)
            self._send_file(frame_path, "image/png")
            return

        if path.startswith("/api/screenshot/"):
            filename = os.path.basename(path)
            if not re.match(r'^[a-zA-Z0-9_\-\.]+\.(png|jpg|jpeg)$', filename):
                self.send_error(400, "Invalid filename")
                return
            shot_path = os.path.join(self.workdir, "screenshots", filename)
            self._send_file(shot_path, "image/png")
            return

        self.send_error(404, f"Unknown path: {path}")

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/event":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            try:
                event = json.loads(body)
                event.setdefault("timestamp", time.time())
                broker.publish(event)
                self._send_json({"ok": True, "event": event})
            except json.JSONDecodeError as e:
                self.send_error(400, f"Invalid JSON: {e}")
            return

        self.send_error(404, f"Unknown path: {path}")

    def _handle_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        q = broker.subscribe()
        try:
            # Send a hello event so the client knows they're connected
            hello = {
                "type": "connected",
                "message": "Connected to agent event stream",
                "timestamp": time.time(),
            }
            self._sse_write(hello)

            while True:
                if q:
                    event = q.pop(0)
                    self._sse_write(event)
                else:
                    # Keep-alive comment every second
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    time.sleep(1)
        except OSError:
            # wave-2b: ConnectionAborted/timeout and friends also die here —
            # a dead client must not traceback a daemon thread to stderr.
            pass
        finally:
            broker.unsubscribe(q)

    def _sse_write(self, event: Dict):
        data = f"event: {event.get('type', 'message')}\n"
        data += f"data: {json.dumps(event)}\n\n"
        self.wfile.write(data.encode())
        self.wfile.flush()


# ---------------------------------------------------------------------------
# HTTP server (D1: THREADED — see ThreadedTCPServer)
# ---------------------------------------------------------------------------

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """D1 (session-18): the SSE handler LOOPS FOREVER while a viewer is
    connected (_handle_sse below), and viewer/live.html calls connectSSE()
    BEFORE initialLoad() — on the single-threaded TCPServer that one SSE
    connection blocked accept() entirely, so every other route (including
    the initialLoad status fetch) deadlocked until the SSE client went
    away: the documented live-viewer deadlock. ThreadingMixIn gives each
    request its own thread; daemon_threads=True keeps Ctrl-C / SIGTERM
    shutdown instant instead of waiting on open SSE streams."""
    daemon_threads = True
    allow_reuse_address = True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Agent server: bridges agent environment to live viewer via SSE.")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--workdir", default="/tmp/agent_session",
                   help="Directory where agent writes scene.glb, scene.json, etc.")
    p.add_argument("--viewer-dir", default=None,
                   help="Directory containing live.html (default: <repo>/viewer)")
    p.add_argument("--no-watch", action="store_true",
                   help="Don't watch scene.glb for changes")
    args = p.parse_args()

    # Find viewer dir
    if args.viewer_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        args.viewer_dir = os.path.normpath(os.path.join(script_dir, "..", "viewer"))

    # Ensure workdir exists
    os.makedirs(args.workdir, exist_ok=True)
    os.makedirs(os.path.join(args.workdir, "frames"), exist_ok=True)
    os.makedirs(os.path.join(args.workdir, "screenshots"), exist_ok=True)

    # Set handler class attributes
    AgentServerHandler.workdir = args.workdir
    AgentServerHandler.viewer_dir = args.viewer_dir

    # Start file watcher
    watcher = None
    if not args.no_watch:
        glb_path = os.path.join(args.workdir, "scene.glb")
        watcher = FileWatcher(glb_path, broker, interval=0.5)
        watcher.start()
        print(f"[server] watching {glb_path} for changes", file=sys.stderr)

    # Start HTTP server (D1: threaded — see ThreadedTCPServer; the old
    # global `socketserver.TCPServer.allow_reuse_address = True` monkey-
    # patch is gone, the attribute lives on the subclass).
    with ThreadedTCPServer(("0.0.0.0", args.port), AgentServerHandler) as httpd:
        print(f"[server] Agent server listening on http://localhost:{args.port}/")
        print(f"[server]   workdir: {args.workdir}")
        print(f"[server]   viewer:  {args.viewer_dir}/live.html")
        print(f"[server]   SSE:     /api/events")
        print(f"[server]   POST events to: /api/event")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[server] shutting down...")
        finally:
            if watcher:
                watcher.stop()


if __name__ == "__main__":
    main()
