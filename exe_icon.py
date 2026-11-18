"""Build a Windows .ico from the repository logo and embed it in Python launchers.

This file is needed on the Windows BUILD computer only, not in the runtime ZIP.
"""
import ctypes
from ctypes import wintypes
import io
from pathlib import Path
import struct
import subprocess
import sys

ICON_PNG = Path("assets") / "siebla-logo.png"


def create_ico(root):
    source = Path(root) / ICON_PNG
    if not source.is_file():
        raise FileNotFoundError(f"找不到 EXE 图标源文件：{source}")
    try:
        from PIL import Image, ImageOps
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image, ImageOps
    # Windows can use small bitmap icons and a 256px PNG-backed icon.
    with Image.open(source) as original:
        original = original.convert("RGBA")
        original.thumbnail((512, 512), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        canvas.alpha_composite(original, ((512-original.width)//2,
                                          (512-original.height)//2))
        cache = Path(root) / "downloads"
        cache.mkdir(parents=True, exist_ok=True)
        path = cache / "siebla-icon.ico"
        canvas.save(path, format="ICO",
                    sizes=[(16,16),(24,24),(32,32),(48,48),
                           (64,64),(128,128),(256,256)])
    return path


def embed_exe_icon(exe_path, ico_path):
    """Write RT_ICON and RT_GROUP_ICON resources with the Windows API."""
    exe_path = Path(exe_path)
    raw = Path(ico_path).read_bytes()
    if len(raw) < 6:
        raise ValueError("ICO 数据为空")
    reserved, icon_type, count = struct.unpack_from("<HHH", raw)
    if reserved or icon_type != 1 or count < 1:
        raise ValueError("ICO 格式无效")
    records = []
    for i in range(count):
        start = 6 + 16*i
        width, height, colors, pad, planes, bits, size, offset = struct.unpack_from(
            "<BBBBHHII", raw, start)
        if offset+size > len(raw):
            raise ValueError("ICO 图像超出文件范围")
        records.append((width,height,colors,pad,planes,bits,raw[offset:offset+size]))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR,wintypes.BOOL]
    kernel32.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel32.UpdateResourceW.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.WORD, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel32.UpdateResourceW.restype = wintypes.BOOL
    kernel32.EndUpdateResourceW.argtypes = [wintypes.HANDLE,wintypes.BOOL]
    kernel32.EndUpdateResourceW.restype = wintypes.BOOL
    handle = kernel32.BeginUpdateResourceW(str(exe_path), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    failed = True
    try:
        entries = []
        for i,(width,height,colors,pad,planes,bits,data) in enumerate(records):
            resource_id = 201+i
            buffer = ctypes.create_string_buffer(data)
            if not kernel32.UpdateResourceW(
                handle,ctypes.c_void_p(3),ctypes.c_void_p(resource_id),
                0x0409,buffer,len(data)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            entries.append(struct.pack("<BBBBHHIH",
                width,height,colors,pad,planes,bits,len(data),resource_id))
        group = struct.pack("<HHH",0,1,len(entries)) + b"".join(entries)
        buffer = ctypes.create_string_buffer(group)
        if not kernel32.UpdateResourceW(
            handle,ctypes.c_void_p(14),ctypes.c_void_p(1),
            0x0409,buffer,len(group)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        failed = False
    finally:
        if not kernel32.EndUpdateResourceW(handle,failed):
            raise ctypes.WinError(ctypes.get_last_error())
