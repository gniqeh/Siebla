"""Small, offline, side-effect-minimizing completion for the browser notebook.

Only accepts a dotted chain of Python identifiers (e.g. df.merge or pd.re).
Never evals expressions, imports a module, calls a function, or invokes a
property getter to obtain suggestions.
"""
import builtins
import inspect
import keyword
import re

MAX_CANDIDATES = 80
PATTERN = re.compile(r"^(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*$|^(?:[A-Za-z_]\w*\.)+$", re.ASCII)


def _static_names(obj):
    """Get module/instance/class attribute names without calling custom __dir__."""
    names = set()
    try:
        namespace = vars(obj)
        if isinstance(namespace, dict):
            names.update(k for k in namespace if isinstance(k, str))
    except (TypeError, ValueError):
        pass
    try:
        classes = inspect.getmro(type(obj))
    except (TypeError, AttributeError):
        classes = ()
    for cls in classes:
        try:
            names.update(k for k in vars(cls) if isinstance(k, str))
        except (TypeError, ValueError):
            pass
    return names


def complete(prefix, namespace):
    """Return replacement candidates for a safe identifier or attribute prefix."""
    if not isinstance(prefix, str) or len(prefix) > 180 or not PATTERN.fullmatch(prefix):
        return []
    if "." not in prefix:
        words = set(namespace) | set(vars(builtins)) | set(keyword.kwlist)
        partial = prefix
    else:
        *chain, partial = prefix.split(".")
        obj = namespace.get(chain[0])
        if obj is None or len(chain) > 6:
            return []
        for part in chain[1:]:
            try:
                obj = inspect.getattr_static(obj, part)
            except (AttributeError, TypeError, ValueError):
                return []
            # Stop at descriptors rather than reading property results.
            if inspect.isdatadescriptor(obj):
                return []
        words = _static_names(obj)

    # Hide private members until user explicitly starts typing an underscore.
    options = [
        word for word in words
        if isinstance(word, str) and word.startswith(partial)
        and (not word.startswith("_") or partial.startswith("_"))
    ]
    return sorted(set(options), key=lambda x: (x != partial, x.lower()))[:MAX_CANDIDATES]
