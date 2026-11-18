"""Browser notebook local persistence and code execution API tests.

Run: py -m unittest discover -s tests -v
"""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import notebook


class NotebookApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="siebla-browser-test-")
        self.addCleanup(self.temp.cleanup)
        self.original_book = notebook.BOOK_FILE
        notebook.BOOK_FILE = Path(self.temp.name) / "Siebla-notebook.json"
        self.addCleanup(lambda: setattr(notebook, "BOOK_FILE", self.original_book))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), notebook.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, path, body=None):
        headers = {"X-Notebook-Token": notebook.TOKEN}
        if body is not None:
            headers["Origin"] = self.base
            headers["Content-Type"] = "application/json"
        request = Request(
            self.base + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers=headers,
            method="POST" if body is not None else "GET",
        )
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def test_save_and_restore(self):
        first = self.request("/book")
        self.assertFalse(first["saved"])
        notebook_data = {
            "format": "siebla-notebook-v1",
            "cells": [{"code": "x=42\nprint(x)", "output": "42\n"}],
        }
        self.assertTrue(self.request("/book", notebook_data)["saved"])
        restored = self.request("/book")
        self.assertEqual(restored["cells"], notebook_data["cells"])
        self.assertTrue(notebook.BOOK_FILE.is_file())
        notebook_data["cells"][0]["code"] = "x=43"
        self.request("/book", notebook_data)
        self.assertEqual(self.request("/book")["cells"][0]["code"], "x=43")

    def test_invalid_notebook_does_not_replace_saved_data(self):
        valid = {"format": "siebla-notebook-v1",
                 "cells": [{"code": "print(1)", "output": ""}]}
        self.request("/book", valid)
        with self.assertRaises(HTTPError) as raised:
            self.request("/book", {"format": "bad", "cells": []})
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(self.request("/book")["cells"], valid["cells"])

    def test_completion_sees_runtime_variables(self):
        result = self.request("/run", {"code": "siebla_completion_example = [1, 2, 3]"})
        self.assertTrue(result["ok"])
        found = self.request("/complete", {"prefix": "siebla_completion_ex"})
        self.assertIn("siebla_completion_example", found["items"])
        members = self.request("/complete", {"prefix": "siebla_completion_example.ap"})
        self.assertIn("append", members["items"])
        unsafe = self.request("/complete", {"prefix": "__import__('os')."})
        self.assertEqual(unsafe["items"], [])

    def test_run_uses_shared_engine(self):
        response = self.request("/run", {"code": "browser_test_number=37"})
        self.assertTrue(response["ok"])
        again = self.request("/run", {"code": "print(browser_test_number+5)"})
        self.assertTrue(again["ok"])
        self.assertEqual(again["stdout"].strip(), "42")


if __name__ == "__main__":
    unittest.main()
