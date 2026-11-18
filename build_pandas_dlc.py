"""Build small offline Siebla ZIP DLCs for pandas + NumPy, each < 20 MB."""
import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
LIMIT = 20_000_000


def write_dlc(destination, wheels):
    if not wheels:
        raise RuntimeError(f"No packages for {destination.name}")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        names = set()
        for wheel in wheels:
            with zipfile.ZipFile(wheel) as package:
                for item in package.infolist():
                    if item.is_dir():
                        continue
                    path = PurePosixPath(item.filename.replace("\\", "/"))
                    if path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
                        raise ValueError(f"Unsafe entry in {wheel.name}: {item.filename}")
                    if item.filename in names:
                        raise ValueError(f"Duplicate path in DLC: {item.filename}")
                    names.add(item.filename)
                    out.writestr(item, package.read(item))
    size = destination.stat().st_size
    print(f"{destination.name}: {size:,} bytes / {LIMIT:,} limit")
    if size > LIMIT:
        destination.unlink()
        raise RuntimeError(f"{destination.name} exceeds 20 MB. Cannot distribute this DLC.")
    return destination


def main():
    parser = argparse.ArgumentParser(description="Build separate NumPy + Pandas DLC ZIPs")
    parser.add_argument("--name", default="Siebla")
    parser.add_argument("--pandas", default="2.2.3")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="siebla-dlc-") as tmp:
        wheel_dir = Path(tmp)
        subprocess.check_call([
            sys.executable, "-m", "pip", "download",
            "--only-binary=:all:", "--platform", "win_amd64",
            "--python-version", "312", "--implementation", "cp",
            "--abi", "cp312", "--dest", str(wheel_dir),
            f"pandas=={args.pandas}",
        ])
        wheels = sorted(wheel_dir.glob("*.whl"))
        numpy = [p for p in wheels if p.name.lower().startswith("numpy-")]
        pandas = [p for p in wheels if p.name.lower().startswith("pandas-")]
        other = [p for p in wheels if p not in numpy and p not in pandas]
        if len(numpy) != 1 or len(pandas) != 1:
            raise RuntimeError(f"Expected NumPy and Pandas wheels; got: {[p.name for p in wheels]}")

        output = ROOT / "dlc_dist"
        output.mkdir(exist_ok=True)
        # Remove the old, oversized combined package to prevent copying it by mistake.
        old = output / f"{args.name}-Pandas.zip"
        if old.is_file():
            old.unlink()

        files = [
            write_dlc(output / f"{args.name}-01-NumPy.zip", numpy),
            write_dlc(output / f"{args.name}-02-Pandas.zip", pandas + other),
        ]
        print("\nDone. On the offline PC, use '加载 DLC' twice, in this order:")
        for path in files:
            print(f"  {path.name}")
        print("Both packages include their Python 3.12 / Windows x64 dependencies.")
        print("No internet or external Python install is needed on the target PC.")
        print("Restart Siebla after loading both packages if import fails in this session.")


if __name__ == "__main__":
    main()
