"""Build the standalone Siebla Windows x64 ZIP (Python 3.12)."""
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "downloads"
PY_ZIP = "python-3.12.10-embed-amd64.zip"
PY_URL = f"https://www.python.org/ftp/python/3.12.10/{PY_ZIP}"
PACKAGES = {"openpyxl": "3.1.5", "et_xmlfile": "2.0.0"}
LIMIT = 20_000_000


def python_archive():
    """Prefer the versioned Python runtime committed to the repository."""
    vendored = ROOT / "runtime" / PY_ZIP
    cached = CACHE / PY_ZIP
    if vendored.is_file():
        archive = vendored
    elif cached.is_file():
        archive = cached
    else:
        raise FileNotFoundError(
            f"Missing Python 3.12 runtime: {vendored}\n"
            f"Download {PY_URL} and commit it under runtime/ "
            "or copy it into downloads/."
        )
    if not zipfile.is_zipfile(archive):
        raise RuntimeError(f"Invalid Python archive: {archive}")
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
        if not {"python.exe", "python312.dll", "python312.zip"}.issubset(names):
            raise RuntimeError(f"Not the expected Python 3.12 embedded runtime: {archive}")
    print("Using bundled Python:", archive)
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
        if not {"python.exe", "python312.dll", "python312.zip"}.issubset(members):
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
    for filename in ("notebook.py", "index.html", "app.js", "style.css"):
        shutil.copy2(ROOT / filename, target / filename)
    (target / "python312._pth").write_text(
        "python312.zip\n.\nLib\\site-packages\n", encoding="utf-8"
    )
    # Compile a tiny windowed launcher: double-click Siebla.exe, no .cmd or console.
    windows = pathlib.Path(__import__("os").environ.get("SystemRoot", r"C:\\Windows"))
    compiler_paths = [
        windows / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
        windows / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
    ]
    compiler = next((p for p in compiler_paths if p.is_file()), None)
    if compiler is None:
        raise RuntimeError(
            "Windows .NET Framework C# compiler (csc.exe) is required to build Siebla.exe"
        )
    subprocess.check_call([
        str(compiler), "/nologo", "/target:winexe",
        "/reference:System.Windows.Forms.dll",
        "/out:" + str(target / "Siebla.exe"),
        str(ROOT / "launcher.cs"),
    ])
    if not (target / "Siebla.exe").is_file():
        raise RuntimeError("Siebla.exe was not generated")
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
