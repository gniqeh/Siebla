"""Siebla DLC v2 packer: maximize each ZIP below 18,000,000 bytes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zlib
import zipfile

ROOT = Path(__file__).resolve().parent
LIMIT = 18_000_000
CHUNK = 256_000
MANIFEST = "siebla-dlc.json"
SAFETY = 12_000


def _compressed_size(data):
    compressor = zlib.compressobj(level=9, wbits=-15)
    return len(compressor.compress(data)) + len(compressor.flush())


def make_volumes(name, version, wheels, output):
    """Pack independently compressed chunks nearly to the byte limit.

    All volumes contain the full manifest. Chunk positions are recorded in it,
    so choosing any one ZIP lets Siebla locate and verify its siblings.
    """
    records = []
    file_specs = []
    seen = set()
    with tempfile.TemporaryDirectory(prefix="siebla-chunks-") as tmp:
        spool_path = Path(tmp) / "payload.bin"
        with spool_path.open("wb") as spool:
            for wheel in wheels:
                with zipfile.ZipFile(wheel) as archive:
                    for info in sorted(archive.infolist(), key=lambda x: x.filename):
                        if info.is_dir():
                            continue
                        path = PurePosixPath(info.filename.replace("\\", "/"))
                        if (path.is_absolute() or ".." in path.parts
                                or ":" in path.parts[0] or info.filename in seen):
                            raise ValueError(f"Unsafe or duplicate wheel path: {info.filename}")
                        seen.add(info.filename)
                        digest = hashlib.sha256()
                        chunks = []
                        size = 0
                        with archive.open(info) as stream:
                            while True:
                                data = stream.read(CHUNK)
                                if not data:
                                    break
                                offset = spool.tell()
                                spool.write(data)
                                digest.update(data)
                                size += len(data)
                                entry = f"payload/{len(records) + 1:07d}.bin"
                                chunk = {
                                    "part": 1, "entry": entry,
                                    "sha256": hashlib.sha256(data).hexdigest()
                                }
                                # Exact raw deflate size plus local/central ZIP headers.
                                overhead = 76 + len(entry.encode("utf-8")) * 2
                                records.append({
                                    "chunk": chunk, "offset": offset, "length": len(data),
                                    "estimated": _compressed_size(data) + overhead
                                })
                                chunks.append(chunk)
                        file_specs.append({
                            "path": info.filename, "size": size,
                            "sha256": digest.hexdigest(), "chunks": chunks
                        })

        def manifest_for(total, part):
            return {
                "format": "siebla-dlc-v2", "name": name,
                "version": version, "total": total,
                "files": file_specs, "part": part
            }

        # The common manifest is stored in every ZIP. Its compressed size is
        # small compared with the payload, but must still be budgeted.
        sample = json.dumps(manifest_for(1, 1), separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")
        manifest_budget = _compressed_size(sample) + 1024
        capacity = LIMIT - manifest_budget - SAFETY - 200
        if capacity <= 0:
            raise RuntimeError("DLC manifest alone exceeds the ZIP size limit")

        def assign_volumes():
            volumes = [[]]
            remaining = capacity
            for record in records:
                cost = record["estimated"]
                if cost > capacity:
                    raise RuntimeError("A single DLC chunk exceeds capacity")
                if cost > remaining and volumes[-1]:
                    volumes.append([])
                    remaining = capacity
                part = len(volumes)
                record["chunk"]["part"] = part
                volumes[-1].append(record)
                remaining -= cost
            return volumes

        volumes = assign_volumes()
        output.mkdir(parents=True, exist_ok=True)
        generated = []
        # Build exact ZIPs, then trim a small chunk from the end of any volume
        # that is larger than the hard limit. No oversize ZIP is delivered.
        with spool_path.open("rb") as spool:
            while True:
                if len(volumes) > 100:
                    raise RuntimeError("DLC requires more than 100 volumes")
                total = len(volumes)
                oversized = None
                attempts = []
                for idx, members in enumerate(volumes, 1):
                    path = output / f"{name}_{idx:02d}.zip"
                    attempts.append(path)
                    with zipfile.ZipFile(
                        path, "w", compression=zipfile.ZIP_DEFLATED,
                        compresslevel=9
                    ) as archive:
                        archive.writestr(
                            MANIFEST,
                            json.dumps(manifest_for(total, idx),
                                       separators=(",", ":"), ensure_ascii=False)
                        )
                        for record in members:
                            spool.seek(record["offset"])
                            archive.writestr(
                                record["chunk"]["entry"],
                                spool.read(record["length"])
                            )
                    if path.stat().st_size > LIMIT:
                        oversized = idx - 1
                        break

                if oversized is None:
                    generated = attempts
                    break

                # Move the final chunk of the first overflowing volume to the
                # beginning of the next one; reassess the entire manifest.
                for path in attempts:
                    path.unlink(missing_ok=True)
                if not volumes[oversized]:
                    raise RuntimeError("DLC manifest exceeds per-volume limit")
                moving = volumes[oversized].pop()
                if oversized + 1 == len(volumes):
                    volumes.append([])
                volumes[oversized + 1].insert(0, moving)
                # Renumber all later chunks; their manifest pointers are shared.
                for number, members in enumerate(volumes, 1):
                    for record in members:
                        record["chunk"]["part"] = number

        for file in generated:
            size = file.stat().st_size
            if size > LIMIT:
                raise RuntimeError(f"Internal error: oversize {file.name}")
            print(f"  {file.name}: {size:,} / {LIMIT:,} bytes ({size / LIMIT:.1%})")
        return generated


