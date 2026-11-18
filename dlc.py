"""Siebla DLC v2: one logical DLC, any number of ZIP volumes, one-file selection."""
import ctypes
from ctypes import wintypes as W
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
EXTENSIONS = ROOT / "extensions"
PENDING = EXTENSIONS / ".pending"
MANIFEST = "siebla-dlc.json"
LIMIT_BYTES = 20_000_000
MAX_EXTRACTED = 900_000_000
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,75}$")
_dll_handles = []


def _json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _safe_path(p):
    if not isinstance(p, str) or "\\" in p or "\x00" in p:
        raise ValueError("DLC 包含非法文件路径")
    path = PurePosixPath(p)
    if not p or path.is_absolute() or any(x in ("", ".", "..") for x in p.split("/")) or ":" in p.split("/")[0]:
        raise ValueError("DLC 包含不安全路径")
    return path


def _identity(m):
    if (not isinstance(m, dict) or m.get("format") != "siebla-dlc-v2"
            or not NAME.fullmatch(str(m.get("name", "")))
            or not isinstance(m.get("total"), int) or not 1 <= m["total"] <= 100
            or not isinstance(m.get("files"), list)):
        raise ValueError("不是 Siebla DLC v2 分卷")
    if not isinstance(m.get("version"), str) or len(m["version"]) > 64:
        raise ValueError("DLC 版本无效")
    for item in m["files"]:
        _safe_path(item["path"])
        if not isinstance(item["size"], int) or item["size"] < 0:
            raise ValueError("DLC 文件大小无效")
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise ValueError("DLC 校验信息无效")
        for chunk in item["chunks"]:
            if not 1 <= chunk["part"] <= m["total"]:
                raise ValueError("DLC 分卷索引无效")
            _safe_path(chunk["entry"])
    signature = {k: v for k, v in m.items() if k != "part"}
    return hashlib.sha256(_json_bytes(signature)).hexdigest()


def _read_manifest(path):
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ValueError("请选择 ZIP 格式的 Siebla DLC")
    if path.stat().st_size > LIMIT_BYTES:
        raise ValueError(f"{path.name} 超过 20 MB 分卷上限")
    with zipfile.ZipFile(path) as z:
        m = json.loads(z.read(MANIFEST).decode("utf-8"))
    signature = _identity(m)
    if not isinstance(m.get("part"), int) or not 1 <= m["part"] <= m["total"]:
        raise ValueError("DLC 分卷编号无效")
    return m, signature


def _pending_path(name):
    return PENDING / (name + ".json")


def list_installed():
    EXTENSIONS.mkdir(exist_ok=True)
    found = {}
    for folder in sorted(EXTENSIONS.iterdir()):
        metadata = folder / "installed.json"
        if not folder.is_dir() or not metadata.is_file():
            continue
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
            name = data["name"]
            if not NAME.fullmatch(name):
                continue
            found[name] = {
                "name": name, "version": data.get("version", ""),
                "status": "正常", "complete": True,
                "detail": "全部分卷已校验并安装；运行时导入仍需验证",
            }
        except (ValueError, KeyError, OSError):
            continue
    if PENDING.is_dir():
        for file in sorted(PENDING.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                name = data["name"]
                if not NAME.fullmatch(name) or name in found:
                    continue
                missing = data.get("missing", [])
                found[name] = {
                    "name": name, "version": data.get("version", ""),
                    "status": "不完整", "complete": False,
                    "detail": "缺少分卷：" + "、".join(missing),
                }
            except (ValueError, KeyError, OSError):
                continue
    return [found[k] for k in sorted(found)]


def installed_summary():
    items = list_installed()
    if not items:
        return "目前没有加载任何 DLC"
    return "\n".join(
        f"{i['name']}（{i['status']}）"
        + (f"\n  {i['detail']}" if i["detail"] else "")
        for i in items
    )


def activate():
    EXTENSIONS.mkdir(exist_ok=True)
    for child in sorted(EXTENSIONS.iterdir()):
        if not child.is_dir() or not (child / "installed.json").is_file():
            continue
        packages = child / "site-packages"
        if not packages.is_dir():
            continue
        path = str(packages)
        if path not in sys.path:
            sys.path.insert(0, path)
        if hasattr(os, "add_dll_directory"):
            for dll_dir in [packages, *sorted(packages.glob("*.libs"))]:
                if dll_dir.is_dir():
                    try:
                        _dll_handles.append(os.add_dll_directory(str(dll_dir)))
                    except OSError:
                        pass
    importlib.invalidate_caches()


def install(source):
    """Select any ZIP volume; discover siblings and install the complete logical DLC."""
    source = Path(source).resolve()
    first, signature = _read_manifest(source)
    name, total = first["name"], first["total"]
    target = EXTENSIONS / name
    if (target / "installed.json").exists():
        return f"{name}（正常）：此前已完整安装，无需再次加载"
    parent = source.parent
    candidates = {}
    for file in parent.glob("*.zip"):
        if not NAME.fullmatch(file.stem):
            continue
        # Fast prefix filter: volume files are Name_01.zip, Name_02.zip, ...
        if not re.fullmatch(re.escape(name) + r"_\d{2,3}", file.stem):
            continue
        m, sig = _read_manifest(file)
        if sig != signature:
            raise ValueError(f"分卷不一致或混用了不同版本：{file.name}")
        if m["part"] in candidates:
            raise ValueError("发现重复的 DLC 分卷编号")
        candidates[m["part"]] = file
    if first["part"] not in candidates:
        candidates[first["part"]] = source
    missing = [f"{name}_{i:02d}.zip" for i in range(1, total + 1) if i not in candidates]
    PENDING.mkdir(parents=True, exist_ok=True)
    pending = _pending_path(name)
    if missing:
        pending.write_text(
            json.dumps({"name": name, "version": first["version"], "missing": missing},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        return f"{name}（不完整）：缺少 " + "、".join(missing) + "。请把全部 ZIP 放到同一文件夹，再任选一个加载。"

    total_size = sum(item["size"] for item in first["files"])
    if total_size > MAX_EXTRACTED or len(first["files"]) > 50000:
        raise ValueError("DLC 解压规模超限")
    if target.exists():
        raise FileExistsError(f"扩展目录已存在：{target}，请先备份或移走此目录")
    with tempfile.TemporaryDirectory(prefix=".install-", dir=EXTENSIONS) as stage_name:
        stage = Path(stage_name)
        packages = stage / "site-packages"
        packages.mkdir()
        opened = {}
        try:
            for part, path in candidates.items():
                z = zipfile.ZipFile(path)
                opened[part] = z
                # All parts repeat identical manifest (except the part number).
                manifest = json.loads(z.read(MANIFEST).decode("utf-8"))
                if _identity(manifest) != signature or manifest["part"] != part:
                    raise ValueError("分卷清单校验失败")
            used_entries = {i: set() for i in opened}
            for item in first["files"]:
                dest = packages.joinpath(*_safe_path(item["path"]).parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                with dest.open("wb") as output:
                    for chunk in item["chunks"]:
                        part, entry, expected = chunk["part"], chunk["entry"], chunk["sha256"]
                        if entry in used_entries[part]:
                            raise ValueError("DLC 分块重复使用")
                        used_entries[part].add(entry)
                        with opened[part].open(entry) as inp:
                            cdigest = hashlib.sha256()
                            while True:
                                data = inp.read(1024 * 1024)
                                if not data:
                                    break
                                size += len(data)
                                if size > item["size"]:
                                    raise ValueError("DLC 文件长度不符")
                                cdigest.update(data)
                                digest.update(data)
                                output.write(data)
                            if cdigest.hexdigest() != expected:
                                raise ValueError(f"分卷数据损坏：{entry}")
                if size != item["size"] or digest.hexdigest() != item["sha256"]:
                    raise ValueError(f"DLC 文件校验失败：{item['path']}")
            (stage / "installed.json").write_text(
                json.dumps({"name": name, "version": first["version"], "total": total,
                            "signature": signature}, ensure_ascii=False), encoding="utf-8")
        finally:
            for z in opened.values():
                z.close()
        shutil.move(str(stage), str(target))
    pending.unlink(missing_ok=True)
    activate()
    return f"{name}（正常）：{total} 个分卷已自动识别、校验并导入。"


def choose_zip_windows():
    """Show a real Windows file picker, allowing sibling-volume discovery."""
    if os.name != "nt":
        raise OSError("该文件选择器仅支持 Windows")
    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", W.DWORD), ("hwndOwner", W.HWND), ("hInstance", W.HINSTANCE),
            ("lpstrFilter", W.LPCWSTR), ("lpstrCustomFilter", W.LPWSTR),
            ("nMaxCustFilter", W.DWORD), ("nFilterIndex", W.DWORD),
            ("lpstrFile", W.LPWSTR), ("nMaxFile", W.DWORD),
            ("lpstrFileTitle", W.LPWSTR), ("nMaxFileTitle", W.DWORD),
            ("lpstrInitialDir", W.LPCWSTR), ("lpstrTitle", W.LPCWSTR),
            ("Flags", W.DWORD), ("nFileOffset", W.WORD), ("nFileExtension", W.WORD),
            ("lpstrDefExt", W.LPCWSTR), ("lCustData", W.LPARAM),
            ("lpfnHook", ctypes.c_void_p), ("lpTemplateName", W.LPCWSTR),
            ("pvReserved", ctypes.c_void_p), ("dwReserved", W.DWORD), ("FlagsEx", W.DWORD),
        ]
    api = ctypes.WinDLL("comdlg32", use_last_error=True)
    api.GetOpenFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    api.GetOpenFileNameW.restype = W.BOOL
    buf = ctypes.create_unicode_buffer(32768)
    dlg = OPENFILENAMEW()
    dlg.lStructSize = ctypes.sizeof(dlg)
    dlg.lpstrFilter = "ZIP 文件 (*.zip)\0*.zip\0\0"
    dlg.lpstrFile = ctypes.cast(buf, W.LPWSTR)
    dlg.nMaxFile = len(buf)
    dlg.lpstrTitle = "选择任意一个 Siebla DLC 分卷"
    dlg.Flags = 0x00001000 | 0x00000800
    if not api.GetOpenFileNameW(ctypes.byref(dlg)):
        return None
    return buf.value


activate()
