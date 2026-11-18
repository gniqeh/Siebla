"""Build one offline ZIP DLC containing pandas and its Windows x64 dependencies."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="Siebla-Pandas")
    p.add_argument("--pandas", default="2.2.3")
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="siebla-dlc-") as folder:
        folder = Path(folder)
        wheels = folder / "wheels"
        wheels.mkdir()
        subprocess.check_call([
            sys.executable, "-m", "pip", "download",
            "--only-binary=:all:", "--platform", "win_amd64",
            "--python-version", "312", "--implementation", "cp",
            "--abi", "cp312", "--dest", str(wheels),
            f"pandas=={args.pandas}",
        ])
        output = ROOT / "dlc_dist"
        output.mkdir(exist_ok=True)
        target = output / (args.name + ".zip")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for wheel in sorted(wheels.glob("*.whl")):
                with zipfile.ZipFile(wheel) as dep:
                    for item in dep.infolist():
                        if item.is_dir():
                            continue
                        if item.filename.startswith(("/", "\\")) or ".." in Path(item.filename).parts:
                            raise ValueError(f"Unsafe wheel path: {item.filename}")
                        z.writestr(item.filename, dep.read(item))
        print("Pandas DLC:", target)
        print(f"Size: {target.stat().st_size / 1e6:.2f} MB")
        print("Transfer as one ZIP. Target computer does not need network or pip.")

if __name__ == "__main__":
    main()
