"""Describe the *current* Siebla runtime to an AI assistant, without Internet access."""
import importlib.util
import platform
import sys

from dlc import list_installed

DESCRIPTIONS = {
    "Siebla-Excel": (
        "表格办公套件",
        "pandas、NumPy、openpyxl、XlsxWriter、RapidFuzz、pyxlsb 等",
        "XLSX 读取与写入、多表按 ID 关联、筛选清洗、去重、汇总、模糊匹配及报表导出",
    ),
    "Siebla-PDF": (
        "PDF 工具套件",
        "pypdf、PyMuPDF、ReportLab、Pillow 等",
        "PDF 合并拆分、页面处理、文本提取、批量生成 PDF 和水印处理",
    ),
    "Siebla-Media": (
        "图片处理套件",
        "Pillow、piexif、ImageHash、NumPy 等",
        "图片尺寸与格式批处理、EXIF 元数据处理、图片近重复检测",
    ),
}

BASE_MODULES = ("openpyxl", "et_xmlfile")
BASE_TASKS = (
    "运行 Python 代码单元格并共享变量；输出文本结果及错误信息；"
    "通过 openpyxl 对 XLSX 进行基础读写；使用 Python 标准库处理 CSV、"
    "JSON、文本、文件夹、ZIP、SQLite、日期和常规统计。"
)


def _available(module):
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def describe_environment():
    """Return a standalone Chinese message suitable for pasting into an LLM."""
    core = [m for m in BASE_MODULES if _available(m)]
    lines = [
        "请基于以下实际运行环境，为我编写可以直接在 Siebla 中执行的 Python 代码。",
        "不要假设这是完整 Jupyter、Conda 或安装了任意第三方模块的普通 Python。",
        "",
        "【运行环境】",
        "软件：Siebla，本地离线 Python 办公笔记本，Windows 64 位便携运行。",
        "Python：" + platform.python_version()
        + "（解释器版本以此处现场检测结果为准）。",
        "代码单元格共享同一 Python 变量环境；支持标准输出、错误显示。",
        "无互联网、无 pip 安装环节，不能在目标电脑临时联网安装依赖。",
        "",
        "【内置能力】",
        BASE_TASKS,
        "当前可检测到的基础第三方模块：" + ("、".join(core) if core else "未检测到") + "。",
        "",
        "【当前 DLC 安装状态】",
    ]
    items = list_installed()
    if not items:
        lines.append("未安装任何 DLC。请只使用 Siebla 内置能力。")
    for item in items:
        name = item["name"]
        status = item["status"]
        version = item.get("version") or "未标记"
        lines.append(f"- {name}：{status}（版本：{version}）。")
        if status != "正常":
            lines.append("  " + item.get("detail", "缺少必要文件。"))
            lines.append("  不要依赖此 DLC 提供的模块。")
            continue
        if name in DESCRIPTIONS:
            label, modules, tasks = DESCRIPTIONS[name]
            lines.append(f"  套件：{label}；计划包含：{modules}。")
            lines.append(f"  可尝试的任务：{tasks}。")
        else:
            lines.append("  这是自定义 DLC，具体模块和用途尚未识别；请先核实 import。")
        lines.append("  状态“正常”只表示分卷校验和安装完成，不代表已通过模块导入或功能测试。")
    lines.extend([
        "",
        "【生成代码时请遵守】",
        "1. 优先使用上面实际存在的基础模块；仅在 DLC 状态为“正常”时使用对应扩展库。",
        "2. 对需要的第三方库先给出简短 import 检查，若导入失败，应给出仅使用现有库的替代方案。",
        "3. 给出完整、可以直接复制到 Siebla 单元格中执行的代码；需要文件路径时用清晰的路径变量。",
        "4. 不要默认存在 Jupyter 专用命令、!pip、图形交互后端、外部命令工具或联网能力。",
        "5. 请根据上述软件能力完成我接下来提出的办公任务。",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_environment())
