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
from urllib.parse import unquote
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
        if self.path == "/dlc":
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("Origin") != origin
                    or self.headers.get("X-Notebook-Token") != TOKEN):
                return self.reply(403, {"error": "Forbidden"})
            temp_name = None
            try:
                name = unquote(self.headers.get("X-DLC-Name", ""))
                if not name.lower().endswith(".zip") or name != Path(name).name:
                    raise ValueError("无效 DLC 文件名")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 220 * 1024 * 1024:
                    return self.reply(413, {"error": "DLC 文件过大"})
                with tempfile.NamedTemporaryFile(dir=WORK, suffix=".zip",
                                                  prefix="siebla-upload-", delete=False) as temp:
                    temp_name = Path(temp.name)
                    remaining = length
                    while remaining:
                        block = self.rfile.read(min(1024 * 1024, remaining))
                        if not block:
                            raise ValueError("不完整的 DLC 上传")
                        temp.write(block)
                        remaining -= len(block)
                # Keep original filename for the installed extension directory.
                import dlc
                source = temp_name.with_name(name)
                if source.exists():
                    raise ValueError("上传文件名冲突")
                temp_name.rename(source)
                temp_name = source
                message = dlc.install(source)
                return self.reply(200, {"message": message})
            except Exception as exc:
                return self.reply(400, {"error": str(exc)})
            finally:
                if temp_name is not None:
                    temp_name.unlink(missing_ok=True)
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
