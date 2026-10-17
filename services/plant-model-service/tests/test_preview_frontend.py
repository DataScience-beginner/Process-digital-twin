"""Tests restricted synthetic P&ID frontend preview. No customer fixtures."""
import importlib.util
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from time import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

SRC = Path(__file__).resolve().parents[1] / 'app' / 'preview_frontend.py'
spec = importlib.util.spec_from_file_location('preview_frontend', SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.fixture
def preview_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), mod.PreviewHandler)
    server.preview_password = 'SyntheticPreviewPassword!2026'
    server.session_key = b'local-testing-secret-do-not-ship-0123456789'
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown(); server.server_close(); thread.join(timeout=2)


def get(server, path='/', headers=None):
    url = f'http://127.0.0.1:{server.server_port}{path}'
    try:
        with urlopen(Request(url, headers=headers or {}), timeout=3) as resp:
            return resp.status, resp.headers, resp.read()
    except HTTPError as e:
        return e.code, e.headers, e.read()


def post(server, password):
    url = f'http://127.0.0.1:{server.server_port}/login'
    from urllib.parse import urlencode
    data = urlencode({'password': password}).encode()
    req = Request(url, data=data, method='POST', headers={'Content-Type':'application/x-www-form-urlencoded'})
    # Do not auto-follow redirect; inspect Set-Cookie directly.
    from urllib.request import build_opener, HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with build_opener(NoRedirect).open(req, timeout=3) as resp:
            return resp.status, resp.headers, resp.read()
    except HTTPError as e:
        return e.code, e.headers, e.read()


def test_health_public_no_private_artifacts(preview_server):
    status, headers, body = get(preview_server, '/healthz')
    assert status == 200 and b'"synthetic-preview"' in body
    assert headers['Cache-Control'] == 'private, no-store'


def test_login_required_for_all_frontend_assets(preview_server):
    status, _, body = get(preview_server)
    assert status == 200 and b'Preview access password' in body
    for path in ['/app.js','/styles.css']:
        assert get(preview_server, path)[0] == 401
    assert b'synthetic' in body.lower()


def test_wrong_password_does_not_set_cookie(preview_server):
    status, headers, body = post(preview_server, 'wrong-value')
    assert status == 401 and headers.get('Set-Cookie') is None
    assert b'Incorrect preview password' in body


def test_correct_login_sets_httponly_secure_cookie(preview_server):
    status, headers, body = post(preview_server, preview_server.preview_password)
    assert status == 303
    cookie = headers['Set-Cookie']
    assert all(x in cookie for x in ['HttpOnly','Secure','SameSite=Strict','dbpreview=v1.'])
    token = cookie.split(';',1)[0]
    status, _, html = get(preview_server, headers={'Cookie': token})
    assert status == 200 and b'P&amp;ID DIGITALIZATION' in html
    assert b'Synthetic demonstration' in html
    assert get(preview_server, '/app.js', {'Cookie':token})[0] == 200
    assert get(preview_server, '/styles.css', {'Cookie':token})[0] == 200


def test_expired_and_tampered_cookie_rejected(preview_server):
    old = mod._sign(int(time()) - 1, preview_server.session_key)
    future = mod._sign(int(time()) + mod.SESSION_SECONDS + 300, preview_server.session_key)
    valid = mod._sign(int(time())+500, preview_server.session_key)
    for cookie in [old, future, valid + '0', 'x.y.z']:
        assert get(preview_server, '/app.js', {'Cookie': 'dbpreview='+cookie})[0] == 401


def test_assets_do_not_call_customer_api_or_store_source():
    js = (SRC.parent.parent/'preview'/'app.js').read_text()
    html = (SRC.parent.parent/'preview'/'index.html').read_text()
    assert 'fetch(' not in js and 'XMLHttpRequest' not in js
    assert 'type="file"' not in html
    assert 'Synthetic demonstration.' in html
    assert 'engineering_approved_physical_connections' not in html


def test_preview_requires_password_and_session_key(monkeypatch):
    monkeypatch.delenv('PREVIEW_ACCESS_PASSWORD', raising=False)
    monkeypatch.delenv('PREVIEW_SESSION_KEY', raising=False)
    with pytest.raises(RuntimeError, match='strong'):
        mod._config()