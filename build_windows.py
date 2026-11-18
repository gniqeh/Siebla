"""Build the standalone Siebla Windows x64 ZIP (Python 3.11)."""
import pathlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "downloads"
PY_ZIP = "python-3.11.9-embed-amd64.zip"
PY_URL = f"https://www.python.org/ftp/python/3.11.9/{PY_ZIP}"
PACKAGES = {"openpyxl": "3.1.5", "et_xmlfile": "2.0.0"}
LIMIT = 20_000_000


def python_archive():
    CACHE.mkdir(exist_ok=True)
    archive = CACHE / PY_ZIP
    if archive.exists():
        if not zipfile.is_zipfile(archive):
            raise RuntimeError(f"Invalid cached Python archive: {archive}")
        print("Using cached Python:", archive)
        return archive
    partial = CACHE / (PY_ZIP + ".part")
    print("Downloading:", PY_URL)
    try:
        urllib.request.urlretrieve(PY_URL, partial)
        if not zipfile.is_zipfile(partial):
            raise RuntimeError("Downloaded file is not a ZIP")
        partial.replace(archive)
    except Exception:
        partial.unlink(missing_ok=True)
        print("Manual download:", PY_URL)
        print("Save the ZIP without extracting it to:", archive)
        raise
    return archive


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


def build():
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise RuntimeError("Run on 64-bit Windows with Python and pip on the builder")
    source = python_archive()
    deps = wheels()
    output = ROOT / "dist"
    target = output / "Siebla"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(source) as z:
        members = set(z.namelist())
        if not {"python.exe", "python311.dll", "python311.zip"}.issubset(members):
            raise RuntimeError("Wrong embedded Python distribution")
        z.extractall(target)
    site = target / "Lib" / "site-packages"
    site.mkdir(parents=True)
    for wheel in deps:
        with zipfile.ZipFile(wheel) as z:
            for member in z.namelist():
                if ".." in pathlib.PurePosixPath(member).parts or member.startswith("/"):
                    raise RuntimeError(f"Unsafe wheel entry: {member}")
            z.extractall(site)
    for info in site.glob("*.dist-info"):
        shutil.rmtree(info)
    for filename in ("notebook.py", "index.html", "app.js", "style.css", "启动笔记本.cmd"):
        shutil.copy2(ROOT / filename, target / filename)
    (target / "python311._pth").write_text(
        "python311.zip\n.\nLib\\site-packages\n", encoding="utf-8"
    )
    (target / "work").mkdir(exist_ok=True)
    final = output / "Siebla.zip"
    with zipfile.ZipFile(final, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(target.rglob("*")):
            if file.is_file():
                z.write(file, file.relative_to(output))
    size = final.stat().st_size
    print(f"Output: {final}\nSize: {size / 1_000_000:.2f} MB")
    if size > LIMIT:
        final.unlink()
        raise RuntimeError(f"Size exceeds {LIMIT:,} bytes")
    print("PASS: within 20 MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
