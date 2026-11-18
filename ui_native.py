"""Siebla native Win32 notebook, built only with Python stdlib and OS APIs."""
import ctypes as C
import json
import os
from ctypes import wintypes as W
from pathlib import Path
from engine import run_cell

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)
os.chdir(WORK)
SAVE_FILE = WORK / "Siebla-notebook.json"

u = C.WinDLL("user32", use_last_error=True)
k = C.WinDLL("kernel32", use_last_error=True)
H = W.HWND
LRESULT = W.LPARAM
WP = W.WPARAM
LP = W.LPARAM
WNDPROC = C.WINFUNCTYPE(LRESULT, H, W.UINT, WP, LP)

class WNDCLASSEXW(C.Structure):
    _fields_ = [
        ("cbSize", W.UINT), ("style", W.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", C.c_int), ("cbWndExtra", C.c_int),
        ("hInstance", W.HINSTANCE), ("hIcon", W.HICON), ("hCursor", W.HANDLE),
        ("hbrBackground", W.HBRUSH), ("lpszMenuName", W.LPCWSTR),
        ("lpszClassName", W.LPCWSTR), ("hIconSm", W.HICON),
    ]

u.CreateWindowExW.restype = H
u.CreateWindowExW.argtypes = [
    W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int,
    H, W.HMENU, W.HINSTANCE, C.c_void_p
]
u.DefWindowProcW.restype = LRESULT
u.DefWindowProcW.argtypes = [H, W.UINT, WP, LP]
u.CallWindowProcW.restype = LRESULT
u.CallWindowProcW.argtypes = [C.c_void_p, H, W.UINT, WP, LP]
u.SetWindowLongPtrW.restype = C.c_void_p
u.SetWindowLongPtrW.argtypes = [H, C.c_int, C.c_void_p]
u.GetWindowTextLengthW.argtypes = [H]
u.GetWindowTextLengthW.restype = C.c_int
u.GetWindowTextW.argtypes = [H, W.LPWSTR, C.c_int]
u.SetWindowTextW.argtypes = [H, W.LPCWSTR]
u.MoveWindow.argtypes = [H, C.c_int, C.c_int, C.c_int, C.c_int, W.BOOL]
u.SendMessageW.restype = LRESULT
u.SendMessageW.argtypes = [H, W.UINT, WP, LP]
u.GetKeyState.restype = W.SHORT
u.GetKeyState.argtypes = [C.c_int]
k.GetModuleHandleW.restype = H
k.GetModuleHandleW.argtypes = [W.LPCWSTR]
u.LoadCursorW.restype = H
u.LoadCursorW.argtypes = [W.HINSTANCE, C.c_void_p]
u.RegisterClassExW.argtypes = [C.POINTER(WNDCLASSEXW)]
u.GetClientRect.argtypes = [H, C.POINTER(W.RECT)]

WS_OVERLAPPEDWINDOW = 0x00CF0000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
ES_MULTILINE = 4
ES_AUTOVSCROLL = 0x40
ES_WANTRETURN = 0x1000
ES_READONLY = 0x800
LBS_NOTIFY = 1
WM_DESTROY, WM_CLOSE, WM_SIZE, WM_COMMAND, WM_KEYDOWN = 2, 16, 5, 273, 256
LB_ADDSTRING, LB_RESETCONTENT, LB_SETCURSEL = 0x180, 0x184, 0x186
LBN_SELCHANGE = 1
VK_RETURN, VK_SHIFT = 13, 16
GWL_WNDPROC = -4
SW_SHOW = 5

class OPENFILENAMEW(C.Structure):
    _fields_ = [
        ("lStructSize", W.DWORD), ("hwndOwner", W.HWND), ("hInstance", W.HINSTANCE),
        ("lpstrFilter", W.LPCWSTR), ("lpstrCustomFilter", W.LPWSTR),
        ("nMaxCustFilter", W.DWORD), ("nFilterIndex", W.DWORD),
        ("lpstrFile", W.LPWSTR), ("nMaxFile", W.DWORD),
        ("lpstrFileTitle", W.LPWSTR), ("nMaxFileTitle", W.DWORD),
        ("lpstrInitialDir", W.LPCWSTR), ("lpstrTitle", W.LPCWSTR),
        ("Flags", W.DWORD), ("nFileOffset", W.WORD), ("nFileExtension", W.WORD),
        ("lpstrDefExt", W.LPCWSTR), ("lCustData", W.LPARAM),
        ("lpfnHook", C.c_void_p), ("lpTemplateName", W.LPCWSTR),
        ("pvReserved", C.c_void_p), ("dwReserved", W.DWORD), ("FlagsEx", W.DWORD)
    ]

common_dialog = C.WinDLL("comdlg32", use_last_error=True)
common_dialog.GetOpenFileNameW.restype = W.BOOL
common_dialog.GetOpenFileNameW.argtypes = [C.POINTER(OPENFILENAMEW)]

def load_dlc():
    file_buffer = C.create_unicode_buffer(32768)
    dlg = OPENFILENAMEW()
    dlg.lStructSize = C.sizeof(dlg)
    dlg.lpstrFilter = "Siebla DLC ZIP (*.zip)\\0*.zip\\0所有文件 (*.*)\\0*.*\\0\\0".replace("\\0", "\0")
    dlg.lpstrFile = C.cast(file_buffer, W.LPWSTR)
    dlg.nMaxFile = len(file_buffer)
    dlg.lpstrTitle = "选择 Siebla DLC 压缩包"
    dlg.Flags = 0x00001000 | 0x00000800  # OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST
    if not common_dialog.GetOpenFileNameW(C.byref(dlg)):
        return
    try:
        from dlc import install
        msg = install(file_buffer.value)
        set_value(controls["status"], msg)
        u.MessageBoxW(None, msg, "Siebla DLC", 0x40)
    except Exception as exc:
        u.MessageBoxW(None, str(exc), "DLC 导入失败", 0x10)

cells = [{"code": 'import sys\nprint("Python", sys.version.split()[0])\nprint("解释器", sys.executable)', "output": ""}]
selected = 0
controls = {}
previous_edit_proc = None

def value(hwnd):
    n = u.GetWindowTextLengthW(hwnd)
    buf = C.create_unicode_buffer(n + 1)
    u.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value

def set_value(hwnd, text):
    u.SetWindowTextW(hwnd, text)

def save_current():
    cells[selected]["code"] = value(controls["code"])

def load_cell(index):
    global selected
    selected = index
    set_value(controls["code"], cells[index]["code"])
    set_value(controls["output"], cells[index]["output"])
    u.SendMessageW(controls["items"], LB_SETCURSEL, index, 0)
    set_value(controls["status"], f"单元格 {index+1}/{len(cells)} · 完全离线")

def refresh():
    u.SendMessageW(controls["items"], LB_RESETCONTENT, 0, 0)
    for i in range(len(cells)):
        label = C.create_unicode_buffer(f" In [{i+1}] ")
        u.SendMessageW(controls["items"], LB_ADDSTRING, 0, C.cast(label, C.c_void_p).value)
    load_cell(min(selected, len(cells) - 1))

def execute():
    save_current()
    result = run_cell(cells[selected]["code"])
    output = (result["stdout"] + result["stderr"]).rstrip()
    cells[selected]["output"] = output or "（执行完成，无文本输出）"
    set_value(controls["output"], cells[selected]["output"])
    set_value(controls["status"], "执行成功" if result["ok"] else "执行失败，查看输出")

def add_cell():
    global selected
    save_current()
    cells.append({"code": "", "output": ""})
    selected = len(cells) - 1
    refresh()
    u.SetFocus(controls["code"])

def save_book():
    save_current()
    SAVE_FILE.write_text(json.dumps({"format": "siebla-notebook-v1", "cells": cells},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    set_value(controls["status"], "已保存至 work/Siebla-notebook.json")

def open_book():
    global selected
    if not SAVE_FILE.exists():
        set_value(controls["status"], "尚未发现 work/Siebla-notebook.json")
        return
    data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    if data.get("format") != "siebla-notebook-v1" or not isinstance(data.get("cells"), list):
        set_value(controls["status"], "不是有效的 Siebla 笔记本")
        return
    candidate = [{"code": str(x.get("code", "")), "output": str(x.get("output", ""))}
                 for x in data["cells"] if isinstance(x, dict)]
    cells[:] = candidate or [{"code": "", "output": ""}]
    selected = 0
    refresh()

@WNDPROC
def edit_proc(hwnd, msg, wparam, lparam):
    if msg == WM_KEYDOWN and wparam == VK_RETURN and u.GetKeyState(VK_SHIFT) < 0:
        execute()
        return 0
    return u.CallWindowProcW(previous_edit_proc, hwnd, msg, wparam, lparam)

@WNDPROC
def window_proc(hwnd, msg, wparam, lparam):
    if msg == WM_COMMAND:
        ident = int(wparam) & 0xFFFF
        notify = (int(wparam) >> 16) & 0xFFFF
        if ident == 100 and notify == LBN_SELCHANGE:
            new_index = int(u.SendMessageW(controls["items"], 0x188, 0, 0))
            if 0 <= new_index < len(cells) and new_index != selected:
                save_current()
                load_cell(new_index)
        elif ident == 101: execute()
        elif ident == 102: add_cell()
        elif ident == 103: save_book()
        elif ident == 104: open_book()
        elif ident == 108: load_dlc()
        return 0
    if msg == WM_SIZE and controls:
        rect = W.RECT()
        u.GetClientRect(hwnd, C.byref(rect))
        width = max(400, rect.right - rect.left)
        height = max(350, rect.bottom - rect.top)
        u.MoveWindow(controls["items"], 12, 12, 130, height-65, True)
        right_x = 152
        content_width = width - right_x - 12
        for key, x, w in (("run", right_x, 85), ("add", right_x+90, 85),
                          ("save", right_x+180, 85), ("open", right_x+270, 85),
                          ("dlc", right_x+360, 95)):
            u.MoveWindow(controls[key], x, 12, w, 32, True)
        code_height = max(120, (height-105)//2)
        u.MoveWindow(controls["code"], right_x, 53, content_width, code_height, True)
        u.MoveWindow(controls["output"], right_x, 63+code_height, content_width,
                     max(80, height-115-code_height), True)
        u.MoveWindow(controls["status"], 12, height-35, width-24, 23, True)
        return 0
    if msg == WM_CLOSE:
        save_current()
        u.DestroyWindow(hwnd)
        return 0
    if msg == WM_DESTROY:
        u.PostQuitMessage(0)
        return 0
    return u.DefWindowProcW(hwnd, msg, wparam, lparam)

def main():
    global previous_edit_proc
    instance = k.GetModuleHandleW(None)
    cls = "SieblaNativeWindow"
    wc = WNDCLASSEXW()
    wc.cbSize = C.sizeof(wc)
    wc.lpfnWndProc = window_proc
    wc.hInstance = instance
    wc.hCursor = u.LoadCursorW(None, C.c_void_p(32512))
    wc.hbrBackground = 6
    wc.lpszClassName = cls
    if not u.RegisterClassExW(C.byref(wc)):
        raise C.WinError(C.get_last_error())
    hwnd = u.CreateWindowExW(0, cls, "Siebla · Python 离线笔记本",
                             WS_OVERLAPPEDWINDOW | WS_VISIBLE, 100, 100, 1000, 650,
                             None, None, instance, None)
    if not hwnd:
        raise C.WinError(C.get_last_error())
    def make(kind, label, ident, style=0):
        return u.CreateWindowExW(0, kind, label, WS_CHILD | WS_VISIBLE | style,
                                 0, 0, 100, 30, hwnd, W.HMENU(ident), instance, None)
    controls["items"] = make("LISTBOX", "", 100, WS_BORDER | WS_VSCROLL | LBS_NOTIFY)
    controls["code"] = make("EDIT", "", 105, WS_BORDER | WS_VSCROLL | ES_MULTILINE |
                             ES_AUTOVSCROLL | ES_WANTRETURN)
    controls["output"] = make("EDIT", "", 106, WS_BORDER | WS_VSCROLL | ES_MULTILINE |
                               ES_AUTOVSCROLL | ES_READONLY)
    controls["run"] = make("BUTTON", "▶ 运行", 101)
    controls["add"] = make("BUTTON", "＋ 新建", 102)
    controls["save"] = make("BUTTON", "保存", 103)
    controls["open"] = make("BUTTON", "打开", 104)
    controls["dlc"] = make("BUTTON", "加载 DLC", 108)
    controls["status"] = make("STATIC", "", 107)
    previous_edit_proc = u.SetWindowLongPtrW(controls["code"], GWL_WNDPROC,
                                              C.cast(edit_proc, C.c_void_p))
    if not previous_edit_proc:
        raise C.WinError(C.get_last_error())
    refresh()
    rect = W.RECT()
    u.GetClientRect(hwnd, C.byref(rect))
    window_proc(hwnd, WM_SIZE, 0, 0)
    u.ShowWindow(hwnd, SW_SHOW)
    u.UpdateWindow(hwnd)
    msg = W.MSG()
    while u.GetMessageW(C.byref(msg), None, 0, 0) > 0:
        u.TranslateMessage(C.byref(msg))
        u.DispatchMessageW(C.byref(msg))

if __name__ == "__main__":
    main()
