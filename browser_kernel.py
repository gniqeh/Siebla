"""Browser-only runtime variable inspection and soft kernel reset.

Never calls repr on arbitrary user-defined objects or evaluates expressions.
"""
import types

from engine import VARIABLES

MAX_VARIABLES = 300
MAX_PREVIEW = 120


def _preview(value):
    cls = type(value)
    if cls in (type(None), bool, int, float, complex, str, bytes):
        return repr(value)[:MAX_PREVIEW]
    if cls in (list, tuple, dict, set, frozenset, bytearray):
        return f"{len(value)} 项"
    if isinstance(value, types.ModuleType):
        return "模块"
    return "（不预览对象内容）"


def list_variables():
    result = []
    for name, value in sorted(VARIABLES.items()):
        if not isinstance(name, str) or name.startswith("_"):
            continue
        cls = type(value)
        result.append({
            "name": name,
            "type": f"{cls.__module__}.{cls.__qualname__}"[:160],
            "preview": _preview(value),
        })
        if len(result) >= MAX_VARIABLES:
            break
    return result


def reset_variables():
    """Soft reset: remove user variables, preserving the server and installed DLCs."""
    VARIABLES.clear()
    VARIABLES["__name__"] = "__main__"
