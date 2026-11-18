"""Build independent Siebla Excel / PDF / Media DLCs, or all three.

Every DLC is self-contained relative to Siebla Core and may be split into
multiple ZIP volumes of at most 18,000,000 bytes. No extra target-PC install.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from dlc_packer import make_volumes

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "dlc_dist"

# Use the same NumPy and Pillow versions when more than one DLC installs them.
# This avoids incompatible duplicates if Excel and Media/PDF are installed together.
NUMPY = "numpy==2.1.3"
PILLOW = "Pillow==11.3.0"

SUITES = {
    "excel": {
        "name": "Siebla-Excel",
        "version": "1.0",
        "requirements": [
            "pandas==2.2.3", NUMPY, "openpyxl==3.1.5",
            "XlsxWriter", "rapidfuzz", "pyxlsb",
        ],
        "modules": ("pandas", "numpy", "openpyxl", "xlsxwriter", "rapidfuzz", "pyxlsb"),
    },
    "pdf": {
        "name": "Siebla-PDF",
        "version": "1.0",
        "requirements": ["pypdf", "PyMuPDF", "reportlab", PILLOW],
        "modules": ("pypdf", "fitz", "reportlab", "PIL"),
    },
    "media": {
        "name": "Siebla-Media",
        "version": "1.0",
        "requirements": [PILLOW, "piexif", "ImageHash", NUMPY],
        "modules": ("PIL", "piexif", "imagehash", "numpy"),
    },
}

# NB: ImageHash resolves scipy and PyWavelets. This increases Media volume
# count, but means Media works when Excel is NOT installed.


def build_one(key):
    suite = SUITES[key]
    name = suite["name"]
    print(f"\n===== {name} =====", flush=True)
    with tempfile.TemporaryDirectory(prefix=f"siebla-{key}-") as tmp:
        wheel_dir = Path(tmp)
        command = [
            sys.executable, "-m", "pip", "download",
            "--only-binary=:all:", "--platform", "win_amd64",
            "--python-version", "312", "--implementation", "cp",
            "--abi", "cp312", "--dest", str(wheel_dir),
            *suite["requirements"],
        ]
        print("Resolving complete Windows x64 Python 3.12 dependencies...", flush=True)
        subprocess.check_call(command)
        wheels = sorted(wheel_dir.glob("*.whl"))
        if not wheels:
            raise RuntimeError(f"No wheels were downloaded for {name}")

        # Isolate package outputs to make the selected ZIP's sibling search
        # unambiguous, even when the user builds all three in one pass.
        target = OUTPUT / name
        target.mkdir(parents=True, exist_ok=True)
        # Remove only this suite's previous numbered volumes.
        for old in target.glob(f"{name}_*.zip"):
            old.unlink()

        # Naming/version/volume manifest is shared across all DLC categories.
        volumes = make_volumes(name, suite["version"], wheels, target)
        total = sum(file.stat().st_size for file in volumes)
        print(f"PASS {name}: {len(volumes)} parts, {total:,} bytes total", flush=True)
        return volumes


def main():
    parser = argparse.ArgumentParser(
        description="Build independent, auto-discoverable Siebla DLC volumes"
    )
    parser.add_argument("--dlc", choices=(*SUITES, "all"),
                        help="excel, pdf, media or all")
    args = parser.parse_args()
    chosen = args.dlc
    if chosen is None and sys.stdin.isatty():
        print("Select DLC to build:")
        print("  1. Siebla-Excel (pandas, NumPy, Excel tools)")
        print("  2. Siebla-PDF   (pypdf, PyMuPDF, reportlab)")
        print("  3. Siebla-Media (Pillow, EXIF, image hashes)")
        print("  4. ALL three independent DLCs")
        selected = input("Enter 1/2/3/4 [4]: ").strip() or "4"
        chosen = {"1": "excel", "2": "pdf", "3": "media", "4": "all"}.get(selected)
        if chosen is None:
            parser.error("Choose 1, 2, 3 or 4")

    keys = list(SUITES) if (chosen or "all") == "all" else [chosen]
    successes, failures = [], []
    for key in keys:
        try:
            parts = build_one(key)
            successes.append((key, len(parts)))
        except Exception as error:
            failures.append((key, str(error)))
            print(f"FAIL {SUITES[key]['name']}: {error}", flush=True)

    print("\n===== DLC build summary =====")
    for key, parts in successes:
        print(f"PASS {SUITES[key]['name']}: {parts} ZIP volumes")
    for key, message in failures:
        print(f"FAIL {SUITES[key]['name']}: {message}")
    if failures:
        raise SystemExit(1)
    print("\nCopy each DLC's entire output folder to the offline PC.")
    print("In Siebla, choose ANY numbered ZIP within that folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
