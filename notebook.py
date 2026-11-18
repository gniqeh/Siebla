"""Siebla local-only notebook server, no third-party server dependencies."""
import ast
import contextlib
import io
import json
import os
import secrets
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
os.chdir(WORK)
TOKEN = secrets.token_urlsafe(24)
VARS = {"__name__": "__main__"}
LOCK = threading.Lock()
MAX_BYTES = 3_000_000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, status, payload, content_type="application/json; charset=utf-8"):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/?token=" + TOKEN:
            return self.reply(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/app.js":
            return self.reply(200, (ROOT / "app.js").read_bytes(), "application/javascript; charset=utf-8")
        if self.path == "/style.css":
            return self.reply(200, (ROOT / "style.css").read_bytes(), "text/css; charset=utf-8")
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if (self.path != "/run" or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                or self.headers.get("Origin") != origin
                or self.headers.get("X-Notebook-Token") != TOKEN):
            return self.reply(403, {"error": "Forbidden"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BYTES:
                return self.reply(413, {"error": "Bad input size"})
            payload = json.loads(self.rfile.read(length))
            code = payload["code"]
            if not isinstance(code, str):
                raise ValueError("Code must be text")
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "Invalid request"})
        stdout, stderr = io.StringIO(), io.StringIO()
        with LOCK:
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    tree = ast.parse(code, filename="<cell>", mode="exec")
                    if tree.body and isinstance(tree.body[-1], ast.Expr):
                        expr = ast.Expression(tree.body.pop().value)
                        if tree.body:
                            exec(compile(tree, "<cell>", "exec"), VARS)
                        result = eval(compile(expr, "<cell>", "eval"), VARS)
                        if result is not None:
                            print(repr(result))
                    else:
                        exec(compile(tree, "<cell>", "exec"), VARS)
                ok = True
            except BaseException:
                traceback.print_exc(file=stderr)
                ok = False
        return self.reply(200, {"ok": ok, "stdout": stdout.getvalue()[-120000:], "stderr": stderr.getvalue()[-120000:]},)

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/?token={TOKEN}"
    print("Siebla running on", url, flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
