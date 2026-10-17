"""Password-gated, read-only P&ID frontend preview.

Standalone service to show a synthetic front-end without permitting client source
uploads or accessing protected customer/engineering data. No backend proxies.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import time
from urllib.parse import parse_qs

ASSET_PATH = Path(__file__).resolve().parent.parent / "preview"
SESSION_SECONDS = 8 * 60 * 60
ALLOWED = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def _config() -> tuple[str, bytes]:
    password = os.environ.get("PREVIEW_ACCESS_PASSWORD", "")
    key = os.environ.get("PREVIEW_SESSION_KEY", "")
    if len(password) < 16 or len(key) < 32:
        raise RuntimeError("Preview requires strong PREVIEW_ACCESS_PASSWORD and PREVIEW_SESSION_KEY")
    return password, key.encode("utf-8")


def _sign(expire: int, key: bytes) -> str:
    signature = hmac.new(key, f"preview:v1:{expire}".encode(), hashlib.sha256).hexdigest()
    return f"v1.{expire}.{signature}"


def _valid(token: str, key: bytes) -> bool:
    try:
        version, expiry, mac = token.split(".")
        if version != "v1" or not expiry.isdecimal() or not (0 < int(expiry) - int(time()) <= SESSION_SECONDS):
            return False
        return hmac.compare_digest(_sign(int(expiry), key), token)
    except (ValueError, TypeError):
        return False


LOGIN_HTML = b'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Digital BDEP - Internal Preview</title><style>body{margin:0;background:#0c182a;color:#f6f9fc;font:15px system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh;display:grid;place-items:center}main{width:min(385px,calc(100% - 48px));background:#14253a;border:1px solid #304057;border-radius:18px;padding:36px;box-shadow:0 24px 70px #0005}.mark{font-weight:800;font-size:17px;letter-spacing:-.5px;display:flex;align-items:center;gap:12px}.logo{background:#43d9b0;color:#08251f;border-radius:9px;padding:10px}h1{font-size:26px;letter-spacing:-.7px;margin:38px 0 8px}p{color:#aebed0;line-height:1.55;margin:0 0 26px}label{display:block;color:#cad7e5;font-size:13px;margin-bottom:8px}input{width:100%;box-sizing:border-box;background:#0d1b2c;color:white;border:1px solid #3e5068;border-radius:9px;padding:13px;font-size:16px}button{width:100%;border:0;background:#4adeb8;color:#08251d;font-weight:800;border-radius:9px;padding:13px;margin-top:16px;font-size:15px;cursor:pointer}small{display:block;margin-top:22px;color:#8496aa;font-size:12px}.error{color:#ffb1ae;font-size:13px;margin:12px 0 0}</style></head><body><main><div class="mark"><span class="logo">DB</span>Digital BDEP</div><h1>Internal workspace preview</h1><p>Sign in to explore the synthetic P&ID digitization frontend. No customer drawings or production services are exposed here.</p><form action="/login" method="post"><label for="password">Preview access password</label><input id="password" type="password" name="password" autocomplete="current-password" required autofocus><button type="submit">Open workspace &rarr;</button></form><small>Restricted staging preview &bull; synthetic demonstration data only</small></main></body></html>'''


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = "DigitalBDEPPreview"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Never log request payloads, headers, cookies or passwords.
        return

    def _respond(self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8", extra=None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        for key, value in extra or []:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        raw = self.headers.get("Cookie", "")
        if len(raw) > 3000:
            return False
        parsed = cookies.SimpleCookie()
        try:
            parsed.load(raw)
            token = parsed.get("dbpreview")
            return bool(token and _valid(token.value, self.server.session_key))
        except cookies.CookieError:
            return False

    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/healthz":
            self._respond(200, b'{"ok":true,"type":"synthetic-preview"}', "application/json")
            return
        if not self._authorized():
            if route in {"/", "/index.html", "/login"}:
                self._respond(200, LOGIN_HTML)
            else:
                self._respond(401, b"Authorization required", "text/plain")
            return
        if route in ALLOWED:
            filename, mime = ALLOWED[route]
            self._respond(200, (ASSET_PATH / filename).read_bytes(), mime)
        elif route == "/logout":
            self._respond(303, b"", extra=[("Location", "/"), ("Set-Cookie", "dbpreview=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0")])
        else:
            self._respond(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/login":
            self._respond(404, b"Not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 < length <= 4096:
            self._respond(400, b"Invalid request", "text/plain")
            return
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" not in content_type:
            self._respond(415, b"Invalid content type", "text/plain")
            return
        supplied = parse_qs(self.rfile.read(length).decode("utf-8", "replace"), keep_blank_values=True).get("password", [""])[0]
        if not hmac.compare_digest(supplied.encode(), self.server.preview_password.encode()):
            # No hint about whether an account or password exists. App service should be rate-limited at edge.
            self._respond(401, LOGIN_HTML.replace(b"</form>", b'<div class="error">Incorrect preview password.</div></form>'))
            return
        expiry = int(time()) + SESSION_SECONDS
        self._respond(303, b"", extra=[("Location", "/"),
            ("Set-Cookie", f"dbpreview={_sign(expiry, self.server.session_key)}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}")])


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    password, secret = _config()
    server = ThreadingHTTPServer((host, port or int(os.environ.get("PORT", "8000"))), PreviewHandler)
    server.preview_password = password
    server.session_key = secret
    print("Digital BDEP synthetic preview ready (password required)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()