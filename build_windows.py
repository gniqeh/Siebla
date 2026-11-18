"""Build one Siebla interface variant with the embedded Python 3.12.10 runtime."""
import argparse
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "downloads"
PY_ZIP = "python-3.12.10-embed-amd64.zip"
PACKAGES = {"openpyxl": "3.1.5", "et_xmlfile": "2.0.0"}
LIMIT = 20_000_000
MODES = ("native", "winforms", "browser")


def python_archive():
    primary = ROOT / "runtime" / PY_ZIP
    cached = CACHE / PY_ZIP
    source = primary if primary.is_file() else cached
    if not source.is_file():
        raise FileNotFoundError(f"Python ZIP is missing: {primary}")
    if not zipfile.is_zipfile(source):
        raise RuntimeError(f"Invalid embedded Python ZIP: {source}")
    with zipfile.ZipFile(source) as z:
        names = set(z.namelist())
        if not {"python.exe", "pythonw.exe", "python312.dll", "python312.zip"}.issubset(names):
            raise RuntimeError(f"Wrong Python distribution: {source}")
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"Corrupt Python ZIP: {bad}")
    return source


def wheels():
    wheel_dir = CACHE / "wheels"
    wheel_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, version in PACKAGES.items():
        matches = list(wheel_dir.glob(f"{name}-{version}-*.whl"))
        if not matches:
            subprocess.check_call([
                sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                "--no-deps", "-d", str(wheel_dir), f"{name}=={version}",
            ])
            matches = list(wheel_dir.glob(f"{name}-{version}-*.whl"))
        if len(matches) != 1:
            raise RuntimeError(f"Missing or ambiguous wheel: {name}=={version}")
        results.append(matches[0])
    return results


def extract_safe(archive, folder):
    with zipfile.ZipFile(archive) as z:
        for entry in z.namelist():
            parts = PurePosixPath(entry.replace("\\", "/")).parts
            if entry.startswith(("/", "\\")) or ".." in parts or (parts and ":" in parts[0]):
                raise RuntimeError(f"Unsafe ZIP path: {entry}")
        z.extractall(folder)


def winforms_compiler():
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    for base in ("Framework64", "Framework"):
        path = windows / "Microsoft.NET" / base / "v4.0.30319" / "csc.exe"
        if path.is_file():
            return path
    raise RuntimeError("Windows Forms variant requires csc.exe on the build computer only")


def assemble(mode):
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise RuntimeError("Build on Windows 64-bit with Python and pip")
    source, dependencies = python_archive(), wheels()
    dist = ROOT / "dist"
    target = dist / ("Siebla-" + mode)
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    extract_safe(source, target)
    site = target / "Lib" / "site-packages"
    site.mkdir(parents=True)
    for wheel in dependencies:
        extract_safe(wheel, site)
    for metadata in site.glob("*.dist-info"):
        shutil.rmtree(metadata)

    files = ["engine.py", "dlc.py", "capabilities.py"]
    if mode == "browser":
        files += ["sitecustomize.py", "notebook.py", "completion.py", "browser_kernel.py", "index.html", "app.js", "style.css"]
    elif mode == "native":
        files += ["sitecustomize.py", "ui_native.py"]
    else:
        files += ["runner.py"]

    for filename in files:
        shutil.copy2(ROOT / filename, target / filename)
    (target / "work").mkdir(exist_ok=True)

    if mode in ("native", "browser"):
        # Browser uses console Python: closing its console ends the local server.
        # Native keeps pythonw.exe to avoid an unwanted console window.
        launcher = "python.exe" if mode == "browser" else "pythonw.exe"
        shutil.copy2(target / launcher, target / "Siebla.exe")
        if mode == "browser":
            (target / "启动浏览器版.cmd").write_text(
                '@echo off\n'
                'title Siebla Browser - 关闭此窗口即退出\n'
                'cd /d "%~dp0"\n'
                '"%~dp0python.exe" "%~dp0notebook.py"\n'
                'if errorlevel 1 pause\n',
                encoding="utf-8",
            )
        path_config = "python312.zip\n.\nLib\\site-packages\nimport site\n"
    else:
        compiler = winforms_compiler()
        subprocess.check_call([
            str(compiler), "/nologo", "/target:winexe",
            "/reference:System.Drawing.dll",
            "/reference:System.Windows.Forms.dll",
            "/reference:System.Web.Extensions.dll",
            "/out:" + str(target / "Siebla.exe"),
            str(ROOT / "winforms_app.cs"),
        ])
        path_config = "python312.zip\n.\nLib\\site-packages\n"

    (target / "python312._pth").write_text(path_config, encoding="utf-8")
    final = dist / f"Siebla-{mode}.zip"
    with zipfile.ZipFile(final, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(target.rglob("*")):
            if file.is_file():
                z.write(file, file.relative_to(dist))
    size = final.stat().st_size
    print(f"UI: {mode}\nOUTPUT: {final}\nSIZE: {size:,} bytes ({size/1e6:.2f} MB)")
    limit = 18_000_000 if mode == "browser" else LIMIT
    if size > limit:
        final.unlink()
        raise RuntimeError(f"Package exceeds {limit:,} bytes ({mode})")
    print(f"PASS: package is within the {limit:,}-byte limit")
    return final


def main():
    parser = argparse.ArgumentParser(description="Siebla Windows x64 offline builder")
    parser.add_argument("--ui", choices=(*MODES, "all"), help="Select frontend or all")
    args = parser.parse_args()
    mode = args.ui
    if mode is None and sys.stdin.isatty():
        print("Select Siebla UI:\n  1. native   - Win32 desktop window (no .NET or browser)\n"
              "  2. winforms - Windows Forms desktop window (.NET Framework)\n"
              "  3. browser - local page opened in the default browser\n"
              "  4. all     - build all three separately")
        choice = input("Enter 1/2/3/4 [1]: ").strip() or "1"
        mode = {"1": "native", "2": "winforms", "3": "browser", "4": "all"}.get(choice)
        if mode is None:
            parser.error("Choose 1, 2, 3 or 4")
    if mode == "all":
        successes, failures = [], []
        for variant in MODES:
            print(f"\n===== Building {variant} =====", flush=True)
            try:
                successes.append(assemble(variant))
            except Exception as exc:
                failures.append((variant, str(exc)))
                print(f"FAILED [{variant}]: {exc}", flush=True)
        print("\nBuild summary:")
        for path in successes:
            print(f"  PASS: {path.name}")
        for variant, error in failures:
            print(f"  FAIL: {variant}: {error}")
        if failures:
            raise SystemExit(1)
        return
    assemble(mode or "native")


if __name__ == "__main__":
    main()
