"""Offline tests for generic Siebla DLC v2 packaging and installation.

Run from the repository root:
    py -m unittest discover -s tests -v

No pip downloads, Windows APIs, or real pandas installation required.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import dlc
from build_pandas_dlc import make_volumes


def wheel(folder, module, size=0):
    path = folder / (module + "-1.0.0-py3-none-any.whl")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(module + "/__init__.py", "NAME = " + repr(module))
        if size:
            z.writestr(module + "/big_payload.bin", bytes((i * 17) % 251 for i in range(size)))
    return path


class DlcTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="siebla-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ext = self.root / "extensions"
        self.old_ext, self.old_pending = dlc.EXTENSIONS, dlc.PENDING
        dlc.EXTENSIONS, dlc.PENDING = self.ext, self.ext / ".pending"
        self.addCleanup(self.restore_paths)

    def restore_paths(self):
        dlc.EXTENSIONS, dlc.PENDING = self.old_ext, self.old_pending

    def make_dlc(self, name, module, size=0):
        folder = self.root / ("source-" + name)
        folder.mkdir()
        package = wheel(folder, module, size)
        out = self.root / name
        return make_volumes(name, "1.0", [package], out)

    def test_missing_volume_then_recovery(self):
        # Seed > 12 MB of incompressible payload so the packer must split.
        import os
        folder = self.root / "source"
        folder.mkdir()
        path = folder / "testpkg-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("testpkg/__init__.py", "VALUE = 1")
            z.writestr("testpkg/payload.bin", os.urandom(13_000_000))
        volumes = make_volumes("Siebla-Test", "1.0", [path], self.root / "Siebla-Test")
        self.assertGreaterEqual(len(volumes), 2)
        removed = volumes[-1]
        backup = self.root / removed.name
        removed.rename(backup)
        message = dlc.install(volumes[0])
        self.assertIn("不完整", message)
        self.assertEqual(dlc.list_installed()[0]["status"], "不完整")
        self.assertFalse((self.ext / "Siebla-Test" / "installed.json").exists())
        backup.rename(removed)
        message = dlc.install(removed)
        self.assertIn("正常", message)
        self.assertEqual(dlc.list_installed()[0]["status"], "正常")
        self.assertTrue((self.ext / "Siebla-Test" / "site-packages" / "testpkg" / "payload.bin").exists())
        self.assertFalse((self.ext / ".pending" / "Siebla-Test.json").exists())

    def test_all_seven_installation_combinations(self):
        import itertools
        names = {
            "Siebla-Excel": "demo_excel",
            "Siebla-PDF": "demo_pdf",
            "Siebla-Media": "demo_media",
        }
        sources = {name: self.make_dlc(name, module) for name, module in names.items()}
        for count in (1, 2, 3):
            for combination in itertools.combinations(names, count):
                with self.subTest(combination=combination):
                    dlc.EXTENSIONS = self.root / ("extensions-" + "-".join(combination))
                    dlc.PENDING = dlc.EXTENSIONS / ".pending"
                    for name in combination:
                        result = dlc.install(sources[name][0])
                        self.assertIn("正常", result)
                    found = {item["name"]: item["status"] for item in dlc.list_installed()}
                    self.assertEqual(found, {name: "正常" for name in combination})
                    for name in combination:
                        self.assertTrue(
                            (dlc.EXTENSIONS / name / "site-packages" /
                             names[name] / "__init__.py").is_file()
                        )


if __name__ == "__main__":
    unittest.main()
