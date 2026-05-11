#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


    def do_POST(self):
        if self.path.split("?", 1)[0] == "/api/run":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8")
                payload = json.loads(raw or "{}")
                code = str(payload.get("code", ""))
                if len(code) > 20000:
                    self.send_json({"ok": False, "error": "代码太长，请缩短后再运行。"}, 400)
                    return
                if "__import__" in code or "subprocess" in code or "os.system" in code:
                    self.send_json({"ok": False, "error": "为了安全，练习区不允许运行系统命令相关代码。"}, 400)
                    return
                with tempfile.TemporaryDirectory(prefix="pystart_run_") as tmp:
                    script = Path(tmp) / "main.py"
                    script.write_text(code, encoding="utf-8")
                    proc = subprocess.run(
                        ["python3", str(script)],
                        cwd=tmp,
                        input="",
                        text=True,
                        capture_output=True,
                        timeout=3,
                        env={"PYTHONIOENCODING": "utf-8", "PATH": os.environ.get("PATH", "")},
                    )
                output = (proc.stdout or "") + (proc.stderr or "")
                self.send_json({"ok": proc.returncode == 0, "output": output or "程序运行完成，但没有 print() 输出。", "returncode": proc.returncode})
            except subprocess.TimeoutExpired:
                self.send_json({"ok": False, "error": "程序运行超时，请检查是否有无法结束的循环。"}, 408)
            except json.JSONDecodeError:
                self.send_json({"ok": False, "error": "请求数据格式不正确。"}, 400)
            except Exception as exc:
                self.send_json({"ok": False, "error": "运行服务出错：" + str(exc)}, 500)
            return
        self.send_json({"error": "not found"}, 404)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/data":
            try:
                with DATA_FILE.open("r", encoding="utf-8") as f:
                    self.send_json(json.load(f))
            except FileNotFoundError:
                self.send_json({"error": "data.json not found"}, 404)
            except json.JSONDecodeError as exc:
                self.send_json({"error": "invalid data.json", "detail": str(exc)}, 500)
            return
        return super().do_GET()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"PyStart backend running: http://127.0.0.1:{port}/")
    print(f"API: http://127.0.0.1:{port}/api/data")
    server.serve_forever()
