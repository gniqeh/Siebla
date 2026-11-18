"""Line-oriented isolated Python executor for the Windows Forms front end."""
import base64
import json
import os
import sys
from pathlib import Path
from engine import run_cell

work = Path(__file__).resolve().parent / "work"
work.mkdir(exist_ok=True)
os.chdir(work)

for raw in sys.stdin.buffer:
    try:
        code = base64.b64decode(raw.strip(), validate=True).decode("utf-8")
        output = run_cell(code)
        payload = json.dumps(output, ensure_ascii=False).encode("utf-8")
    except Exception as e:
        payload = json.dumps({"ok": False, "stdout": "", "stderr": str(e)}).encode("utf-8")
    sys.stdout.buffer.write(base64.b64encode(payload) + b"\n")
    sys.stdout.buffer.flush()
