"""Compact copy-and-paste Python environment summary for an AI model."""
import importlib.util
import platform

from dlc import list_installed

# These are descriptions of packaged modules, not proofs that imports work.
DLC_MODULES = {
    "Siebla-Excel": "pandas, numpy, openpyxl, xlsxwriter, rapidfuzz, pyxlsb",
    "Siebla-PDF": "pypdf, fitz(PyMuPDF), reportlab, PIL",
    "Siebla-Media": "PIL(Pillow), piexif, imagehash, numpy",
}


def _found(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def describe_environment():
    """Only report environment, available packages and offline restriction."""
    baseline = [name for name in ("openpyxl", "et_xmlfile") if _found(name)]
    lines = [
        f"环境：Windows 便携 Python {platform.python_version()}，代码单元格共享变量。",
        "内置：" + (", ".join(baseline) if baseline else "未检测到第三方库")
        + "；Python 标准库。",
    ]
    items = list_installed()
    if items:
        for item in items:
            name = item["name"]
            if item["status"] == "正常":
                modules = DLC_MODULES.get(name)
                lines.append(f"DLC：{name}（已安装）"
                             + (f"；模块：{modules}" if modules else "；模块未知"))
            else:
                lines.append(f"DLC：{name}（不完整，不可用）")
    else:
        lines.append("DLC：无。")
    lines.append("注意：完全离线，不能联网或 pip 安装新库；仅使用已具备的模块（DLC 安装不等于 import 验证通过）。")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_environment())
