"""Offline completion tests: dynamic namespace, dotted members, no code evaluation."""
import unittest
from completion import complete


class Unsafe:
    def __init__(self):
        self.accessed = 0
        self.safe_value = 42

    @property
    def dangerous(self):
        raise RuntimeError("completion must never execute properties")

    def method(self):
        return None


class CompletionTests(unittest.TestCase):
    def test_namespace_variables(self):
        items = complete("da", {"dataframe": object(), "data": object()})
        self.assertIn("dataframe", items)
        self.assertIn("data", items)

    def test_module_style_and_instance_members(self):
        item = Unsafe()
        self.assertIn("method", complete("x.met", {"x": item}))
        self.assertIn("safe_value", complete("x.safe", {"x": item}))
        self.assertIn("dangerous", complete("x.dan", {"x": item}))
        self.assertEqual(item.accessed, 0)

    def test_never_evaluates_expressions(self):
        item = Unsafe()
        self.assertEqual(complete("x.method().", {"x": item}), [])
        self.assertEqual(complete("__import__('os').", {"x": item}), [])
        self.assertEqual(complete("x[0].", {"x": item}), [])
        self.assertEqual(complete("x.dangerous.", {"x": item}), [])
        self.assertEqual(item.accessed, 0)

    def test_unknown_and_private(self):
        item = Unsafe()
        self.assertEqual(complete("missing.", {"x": item}), [])
        self.assertNotIn("__class__", complete("x.", {"x": item}))
        self.assertIn("__class__", complete("x.__", {"x": item}))


if __name__ == "__main__":
    unittest.main()
