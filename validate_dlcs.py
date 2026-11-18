"""Offline Windows x64 smoke test: verify 3 standalone DLCs and all 7 combos.

Run after building the Siebla core and selected DLC ZIPs:
    py build_windows.py --ui browser
    py build_dlcs.py --dlc all
    py validate_dlcs.py

Uses the bundled Python 3.12, not the developer's Python environment.
Runs each combination in an isolated process and temporary extension directory.
"""
import itertools
from pathlib import Path
import subprocess
import sys
import tempfile

from build_dlcs import OUTPUT, SUITES

ROOT = Path(__file__).resolve().parent

SCRIPT = r"""
import importlib
import json
from pathlib import Path
import sys

import dlc

folder = Path(sys.argv[1])
specs = json.loads(sys.argv[2])
dlc.EXTENSIONS = folder
dlc.PENDING = folder / ".pending"

for spec in specs:
    parts = sorted(Path(spec["folder"]).glob(spec["name"] + "_*.zip"))
    if not parts:
        raise RuntimeError("Missing DLC ZIP volumes for " + spec["name"])
    # Deliberately select the LAST volume to verify any-part selection.
    message = dlc.install(parts[-1])
    if "（正常）" not in message:
        raise RuntimeError("Not installed: " + message)

statuses = {entry["name"]: entry["status"] for entry in dlc.list_installed()}
if statuses != {spec["name"]: "正常" for spec in specs}:
    raise RuntimeError("Incorrect DLC status: " + repr(statuses))

for spec in specs:
    for module in spec["modules"]:
        imported = importlib.import_module(module)
        print("  imported", module, getattr(imported, "__version__", ""))
print("  OK:", ", ".join(sorted(statuses)))
"""


def main():
    python_exe = next(
        (ROOT / "dist" / ("Siebla-" + ui) / "python.exe"
         for ui in ("browser", "native", "winforms")
         if (ROOT / "dist" / ("Siebla-" + ui) / "python.exe").is_file()),
        None,
    )
    if python_exe is None:
        raise SystemExit("Build Siebla core first: py build_windows.py --ui browser")
    if sys.platform != "win32":
        raise SystemExit("This test must run on Windows 64-bit")

    import json
    failed = []
    keys = list(SUITES)
    with tempfile.TemporaryDirectory(prefix="siebla-dlc-validation-") as temp:
        for count in (1, 2, 3):
            for choice in itertools.combinations(keys, count):
                label = "+".join(choice)
                specs = [
                    {"name": SUITES[key]["name"],
                     "folder": str(OUTPUT / SUITES[key]["name"]),
                     "modules": SUITES[key]["modules"]}
                    for key in choice
                ]
                local = Path(temp) / label
                print(f"\n===== Testing {label} =====", flush=True)
                result = subprocess.run(
                    [str(python_exe), "-c", SCRIPT, str(local),
                     json.dumps(specs, ensure_ascii=False)],
                    cwd=python_exe.parent, text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=300, errors="replace",
                )
                print(result.stdout)
                if result.returncode:
                    failed.append(label)
                else:
                    print(f"PASS: {label}")

    if failed:
        print("FAILED:", ", ".join(failed))
        raise SystemExit(1)
    print("\nPASS: all 7 independent/combined DLC installations and imports")


if __name__ == "__main__":
    main()
