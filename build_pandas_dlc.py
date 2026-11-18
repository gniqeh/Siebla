"""Create generic Siebla DLC v2 volumes for Python 3.12 Windows x64 pandas."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
LIMIT = 20_000_000
CHUNK = 5_000_000
VOLUME_BUDGET = 12_000_000
MANIFEST = "siebla-dlc.json"


def make_volumes(name, version, wheels, output):
    # ZIP archives contain arbitrary module files. Each file may span volumes.
    files = []
    volumes = [[]]
    volume_size = 0
    item_number = 0
    seen = set()
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            for info in sorted(archive.infolist(), key=lambda x: x.filename):
                if info.is_dir():
                    continue
                path = PurePosixPath(info.filename.replace("\\", "/"))
                if (path.is_absolute() or ".." in path.parts or ":" in path.parts[0]
                        or info.filename in seen):
                    raise ValueError(f"Unsafe or duplicate wheel path: {info.filename}")
                seen.add(info.filename)
                chunks = []
                digest = hashlib.sha256()
                size = 0
                with archive.open(info) as stream:
                    while True:
                        data = stream.read(CHUNK)
                        if not data:
                            break
                        if volume_size + len(data) > VOLUME_BUDGET and volumes[-1]:
                            volumes.append([])
                            volume_size = 0
                        part = len(volumes)
                        item_number += 1
                        entry = f"payload/{item_number:07d}.bin"
                        chunk_hash = hashlib.sha256(data).hexdigest()
                        chunks.append({"part": part, "entry": entry, "sha256": chunk_hash})
                        volumes[-1].append((entry, data))
                        digest.update(data)
                        size += len(data)
                        volume_size += len(data)
                files.append({"path": info.filename, "size": size,
                              "sha256": digest.hexdigest(), "chunks": chunks})
    # Avoid empty trailing parts (an empty file is represented by zero chunks).
    total = len(volumes)
    if total > 100:
        raise RuntimeError("DLC exceeds maximum 100 volumes")
    common = {"format": "siebla-dlc-v2", "name": name, "version": version,
              "total": total, "files": files}
    output.mkdir(exist_ok=True, parents=True)
    paths = []
    for idx, payload in enumerate(volumes, 1):
        path = output / f"{name}_{idx:02d}.zip"
        manifest = dict(common, part=idx)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr(MANIFEST, json.dumps(manifest, separators=(",", ":"), ensure_ascii=False))
            for entry, data in payload:
                z.writestr(entry, data)
        size = path.stat().st_size
        if size > LIMIT:
            path.unlink()
            raise RuntimeError(f"{path.name}: {size:,} bytes exceeds {LIMIT:,}")
        paths.append(path)
        print(f"  {path.name}: {size:,} bytes")
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="PandasDLC")
    parser.add_argument("--pandas", default="2.2.3")
    args = parser.parse_args()
    if not args.name.isascii() or not args.name.replace("-", "").replace("_", "").isalnum():
        parser.error("Name must contain ASCII letters, digits, dashes or underscores")
    with tempfile.TemporaryDirectory(prefix="siebla-pandas-") as temp:
        wheel_dir = Path(temp)
        subprocess.check_call([
            sys.executable, "-m", "pip", "download", "--only-binary=:all:",
            "--platform", "win_amd64", "--python-version", "312",
            "--implementation", "cp", "--abi", "cp312",
            "--dest", str(wheel_dir), f"pandas=={args.pandas}",
        ])
        wheels = sorted(wheel_dir.glob("*.whl"))
        if not any(p.name.lower().startswith("numpy-") for p in wheels):
            raise RuntimeError("NumPy wheel missing")
        if not any(p.name.lower().startswith("pandas-") for p in wheels):
            raise RuntimeError("Pandas wheel missing")
        out = ROOT / "dlc_dist"
        for old in out.glob(args.name + "_*.zip") if out.exists() else []:
            old.unlink()
        print(f"Creating {args.name} from {len(wheels)} wheels:")
        paths = make_volumes(args.name, args.pandas, wheels, out)
        print(f"DONE: {len(paths)} volumes; copy all ZIPs into ONE folder.")
        print("In Siebla select ANY volume to import the whole DLC.")
        print("All volumes <= 20,000,000 bytes.")


if __name__ == "__main__":
    main()
