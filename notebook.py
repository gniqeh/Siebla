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
import tempfile
import dlc  # Activate previously installed DLCs in browser sessions.
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
BOOK_FILE = WORK / 'Siebla-notebook.json'


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


    def authorized(self, require_origin=False):
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected or self.headers.get("X-Notebook-Token") != TOKEN:
            return False
        return not require_origin or self.headers.get("Origin") == "http://" + expected

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_BYTES:
            raise ValueError("文件为空或超过容量限制")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/book":
            if not self.authorized():
                return self.reply(403, {"error": "Forbidden"})
            if not BOOK_FILE.exists():
                return self.reply(200, {"format": "siebla-notebook-v1", "cells": [], "saved": False})
            try:
                book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
                return self.reply(200, {"format": "siebla-notebook-v1",
                                        "cells": book.get("cells", []), "saved": True})
            except (OSError, ValueError):
                return self.reply(500, {"error": "笔记本读取失败，请检查 work 文件夹"})
        if self.path == "/capabilities":
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("X-Notebook-Token") != TOKEN):
                return self.reply(403, {"error": "Forbidden"})
            from capabilities import describe_environment
            return self.reply(200, {"text": describe_environment()})
        if self.path == "/dlc-status":
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("X-Notebook-Token") != TOKEN):
                return self.reply(403, {"error": "Forbidden"})
            import dlc
            return self.reply(200, {"installed": dlc.list_installed()})
        if self.path == "/?token=" + TOKEN:
            return self.reply(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/app.js":
            return self.reply(200, (ROOT / "app.js").read_bytes(), "application/javascript; charset=utf-8")
        if self.path == "/style.css":
            return self.reply(200, (ROOT / "style.css").read_bytes(), "text/css; charset=utf-8")
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/book":
            if not self.authorized(require_origin=True):
                return self.reply(403, {"error": "Forbidden"})
            try:
                data = self.read_json_body()
                cells = data.get("cells")
                if (data.get("format") != "siebla-notebook-v1"
                        or not isinstance(cells, list) or len(cells) > 1000):
                    raise ValueError("笔记本格式无效")
                cleaned = []
                for cell in cells:
                    if not isinstance(cell, dict) or not isinstance(cell.get("code"), str):
                        raise ValueError("单元格格式无效")
                    output = cell.get("output", "")
                    if not isinstance(output, str):
                        raise ValueError("输出格式无效")
                    cleaned.append({"code": cell["code"], "output": output[:120000]})
                with LOCK:
                    with tempfile.NamedTemporaryFile(
                        dir=WORK, prefix=".siebla-book-", suffix=".tmp",
                        mode="w", encoding="utf-8", delete=False
                    ) as tmp:
                        target = Path(tmp.name)
                        json.dump({"format": "siebla-notebook-v1", "cells": cleaned},
                                  tmp, ensure_ascii=False)
                    os.replace(target, BOOK_FILE)
                return self.reply(200, {"saved": True})
            except (ValueError, OSError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if self.path == "/dlc-select":
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("Origin") != origin
                    or self.headers.get("X-Notebook-Token") != TOKEN):
                return self.reply(403, {"error": "Forbidden"})
            try:
                from dlc import choose_zip_windows, install
                selected = choose_zip_windows()
                if not selected:
                    return self.reply(200, {"cancelled": True})
                message = install(selected)
                return self.reply(200, {"message": message, "installed": dlc.list_installed()})
            except Exception as exc:
                return self.reply(400, {"error": str(exc)})
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
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("Siebla Browser | 关闭此窗口即退出")
    except (AttributeError, OSError):
        pass
    print("=========================================", flush=True)
    print("Siebla Browser - 本地服务正在运行", flush=True)
    print("关闭这个命令行窗口，即退出 Siebla 并释放文件夹。", flush=True)
    print("仅关闭浏览器页面不会结束本地服务。", flush=True)
    print("Siebla running on", url, flush=True)
    print("=========================================", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
