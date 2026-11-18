"""Start the selected UI only when the bundled pythonw.exe is renamed Siebla.exe."""
import sys
from pathlib import Path

if Path(sys.executable).name.lower() == "siebla.exe":
    try:
        import os
        os.chdir(Path(__file__).resolve().parent / "work")
        if (Path(__file__).resolve().parent / "ui_native.py").is_file():
            from ui_native import main
        else:
            from notebook import main
        main()
    except BaseException:
        import traceback
        work = Path(__file__).resolve().parent / "work"
        work.mkdir(exist_ok=True)
        (work / "siebla-startup-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
