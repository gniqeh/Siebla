"""Simple offline DLC ZIP importer. ZIP contains Python packages at its root."""
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
EXTENSIONS = ROOT / "extensions"
MAX_UNPACKED = 650 * 1024 * 1024
MAX_FILES = 25000
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,90}$")


def activate():
    """Make previously installed DLCs importable on process startup."""
    EXTENSIONS.mkdir(exist_ok=True)
    for child in sorted(EXTENSIONS.iterdir()):
        if child.is_dir() and (child / "installed.json").is_file():
            path = str(child / "site-packages")
            if Path(path).is_dir() and path not in sys.path:
                sys.path.insert(0, path)
                if hasattr(os, "add_dll_directory"):
                    # DLL directories must stay alive for native Python wheels.
                    for dll_dir in [Path(path), *Path(path).glob("*.libs")]:
                        if dll_dir.is_dir():
                            _dll_handles.append(os.add_dll_directory(str(dll_dir)))
    importlib.invalidate_caches()

_dll_handles = []


def install(source):
    """Install a trusted ZIP with library files directly or under site-packages/."""
    source = Path(source).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".zip":
        raise ValueError("请选择存在的 .zip 文件")
    name = source.stem
    if not _NAME.fullmatch(name) or name in {".", ".."}:
        raise ValueError("DLC 文件名只支持英文字母、数字、点、下划线、横线")
    if source.stat().st_size > 220 * 1024 * 1024:
        raise ValueError("DLC ZIP 过大")
    EXTENSIONS.mkdir(exist_ok=True)
    target = EXTENSIONS / name
    if target.exists():
        raise FileExistsError(f"DLC {name} 已安装，请使用不同文件名，或先卸载旧版")
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES or sum(item.file_size for item in entries) > MAX_UNPACKED:
            raise ValueError("DLC 解压容量超限")
        for item in entries:
            raw = item.filename
            p = PurePosixPath(raw.replace("\\", "/"))
            if (p.is_absolute() or ".." in p.parts or not p.parts
                    or ":" in p.parts[0] or raw.startswith(("/", "\\"))):
                raise ValueError("DLC 包含不安全路径")
            if stat.S_ISLNK((item.external_attr >> 16) & 0xFFFF):
                raise ValueError("不允许符号链接")
        if not entries:
            raise ValueError("DLC ZIP 为空")
        with tempfile.TemporaryDirectory(prefix=".siebla-", dir=EXTENSIONS) as tmp:
            stage = Path(tmp)
            content = stage / "site-packages"
            content.mkdir()
            for item in entries:
                parts = PurePosixPath(item.filename.replace("\\", "/")).parts
                if parts[0] == "site-packages":
                    parts = parts[1:]
                if not parts:
                    continue
                dest = content.joinpath(*parts)
                if item.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as read, dest.open("wb") as write:
                    shutil.copyfileobj(read, write)
            if not any(content.iterdir()):
                raise ValueError("没有发现可安装的包文件")
            (stage / "installed.json").write_text(
                json.dumps({"name": name, "filename": source.name},
                           ensure_ascii=False), encoding="utf-8")
            # Move only after successful extraction, leaving no partial DLC.
            shutil.move(str(stage), str(target))
    activate()
    return f"已加载 DLC：{name}。可以尝试 import 对应的 Python 库。"


activate()
