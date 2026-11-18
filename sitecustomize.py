"""Siebla startup hook used by the copied pythonw.exe windowed launcher."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if Path(sys.executable).name.lower() == "siebla.exe":
    try:
        import os
        work = ROOT / "work"
        work.mkdir(exist_ok=True)
        os.chdir(work)
        if (ROOT / "ui_native.py").is_file():
            from ui_native import main
        elif (ROOT / "notebook.py").is_file():
            from notebook import main
        else:
            raise RuntimeError("No Siebla UI module found in the package")
        main()
    except BaseException:
        import traceback
        details = traceback.format_exc()
        try:
            work = ROOT / "work"
            work.mkdir(exist_ok=True)
            log = work / "siebla-startup-error.txt"
            log.write_text(details, encoding="utf-8")
        except Exception:
            log = ROOT / "siebla-startup-error.txt"
            try:
                log.write_text(details, encoding="utf-8")
            except Exception:
                pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                "Siebla 无法启动。\\n错误日志位置：\\n"
                + str(log) + "\\n\\n" + details[-1100:],
                "Siebla 启动错误",
                0x10
            )
        except Exception:
            pass
        raise
