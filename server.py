#!/usr/bin/env python3
"""
motd server — tiny HTTP server for Message of the Day

Endpoints:
  GET /          → HTML portal (index.html)
  GET /motd      → random message as plain text  (curl-friendly)
  GET /motd.json → random message as JSON        (machine-friendly)
  GET /all.json  → full message list

Query params (on /motd and /motd.json):
  ?tag=funny|tech|motivation|kindness|wisdom|courage

Usage:
  python3 server.py [--host 0.0.0.0] [--port 8000] [--messages messages.json]

Fail-safe: if messages.json is missing or malformed, every endpoint returns
a hardcoded fallback so the server never 500s on clients.
"""

import argparse
import json
import os
import random
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# optional: generator support (only active if ANTHROPIC_API_KEY is set)
_GENERATOR_DIR = Path(__file__).parent / "generator"
sys.path.insert(0, str(_GENERATOR_DIR))

FALLBACK = {
    "text": "Keep going. You're doing better than you think.",
    "author": "Anonymous",
    "tag": "kindness",
}


def load_messages(path: str) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text())
        msgs = data.get("messages", [])
        if isinstance(msgs, list) and msgs:
            return msgs
    except Exception:
        pass
    return [FALLBACK]


def pick(messages: list[dict], tag: str | None) -> dict:
    pool = [m for m in messages if m.get("tag") == tag] if tag else messages
    return random.choice(pool) if pool else random.choice(messages)


def plain_text(msg: dict) -> str:
    return f'"{msg["text"]}"\n  — {msg["author"]}\n'


class Handler(BaseHTTPRequestHandler):
    messages: list[dict] = [FALLBACK]

    def log_message(self, fmt, *args):  # quieter logs
        print(f"  {self.address_string()} {fmt % args}")

    def _qs(self) -> dict:
        return parse_qs(urlparse(self.path).query)

    def _tag(self) -> str | None:
        return self._qs().get("tag", [None])[0]

    def _send(self, status: int, content_type: str, body: str | bytes):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_today(self):
        """Serve the AI-generated MOTD (requires ANTHROPIC_API_KEY)."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            msg = {**FALLBACK, "note": "Set ANTHROPIC_API_KEY to enable AI-generated messages"}
            self._send(200, "application/json", json.dumps(msg))
            return
        try:
            from today import get_today_motd  # generator/today.py
            result = get_today_motd()
            self._send(200, "application/json", json.dumps(result))
        except Exception as e:
            self._send(200, "application/json",
                       json.dumps({**FALLBACK, "error": str(e)}))

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            html_file = Path(__file__).parent / "index.html"
            if html_file.exists():
                self._send(200, "text/html; charset=utf-8", html_file.read_bytes())
            else:
                self._send(404, "text/plain", "index.html not found")

        elif path == "/motd":
            msg = pick(self.messages, self._tag())
            self._send(200, "text/plain; charset=utf-8", plain_text(msg))

        elif path == "/motd.json":
            msg = pick(self.messages, self._tag())
            self._send(200, "application/json", json.dumps(msg))

        elif path == "/motd/today":
            self._send_today()

        elif path == "/all.json":
            self._send(200, "application/json",
                       json.dumps({"messages": self.messages}))

        else:
            # serve static files (css, js, etc.) from same directory
            static = Path(__file__).parent / path.lstrip("/")
            if static.is_file():
                ct = "text/plain"
                if path.endswith(".json"): ct = "application/json"
                elif path.endswith(".js"):   ct = "application/javascript"
                elif path.endswith(".css"):  ct = "text/css"
                self._send(200, ct, static.read_bytes())
            else:
                self._send(404, "text/plain", "not found")


def main():
    parser = argparse.ArgumentParser(description="MOTD server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--messages",
                        default=str(Path(__file__).parent / "messages.json"))
    args = parser.parse_args()

    Handler.messages = load_messages(args.messages)
    print(f"  Loaded {len(Handler.messages)} messages from {args.messages}")
    print(f"  Serving on http://{args.host}:{args.port}")
    print(f"  Plain text:  http://{args.host}:{args.port}/motd")
    print(f"  JSON:        http://{args.host}:{args.port}/motd.json")
    if os.environ.get("ANTHROPIC_API_KEY"):
        print(f"  AI today:    http://{args.host}:{args.port}/motd/today  (cached 12h)")
    else:
        print(f"  AI today:    set ANTHROPIC_API_KEY to enable /motd/today")
    print()

    try:
        HTTPServer((args.host, args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
