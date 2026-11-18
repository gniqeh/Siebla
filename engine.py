"""Shared Python cell execution engine for Siebla."""
import ast
import contextlib
import io
import traceback

VARIABLES = {"__name__": "__main__"}

def run_cell(code):
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            tree = ast.parse(code, filename="<Siebla cell>", mode="exec")
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                expr = ast.Expression(tree.body.pop().value)
                if tree.body:
                    exec(compile(tree, "<Siebla cell>", "exec"), VARIABLES)
                result = eval(compile(expr, "<Siebla cell>", "eval"), VARIABLES)
                if result is not None:
                    print(repr(result))
            else:
                exec(compile(tree, "<Siebla cell>", "exec"), VARIABLES)
        ok = True
    except BaseException:
        traceback.print_exc(file=stderr)
        ok = False
    return {"ok": ok, "stdout": stdout.getvalue()[-120000:], "stderr": stderr.getvalue()[-120000:]}
