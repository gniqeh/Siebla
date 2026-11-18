"""Regression tests for Siebla's dynamic AI capability handoff."""
import unittest
from unittest.mock import patch

import capabilities


class CapabilityDescriptionTests(unittest.TestCase):
    def test_no_dlc_is_not_advertised(self):
        with patch.object(capabilities, "list_installed", return_value=[]):
            description = capabilities.describe_environment()
        self.assertIn("未安装任何 DLC", description)
        self.assertNotIn("可尝试的任务：PDF", description)
        self.assertNotIn("可尝试的任务：XLSX", description)

    def test_only_excel_does_not_imply_pdf_or_media(self):
        installed = [{
            "name": "Siebla-Excel", "status": "正常",
            "version": "1.0", "detail": "全部分卷已校验并安装",
        }]
        with patch.object(capabilities, "list_installed", return_value=installed):
            description = capabilities.describe_environment()
        self.assertIn("Siebla-Excel：正常", description)
        self.assertIn("pandas", description)
        self.assertNotIn("Siebla-PDF：正常", description)
        self.assertNotIn("Siebla-Media：正常", description)

    def test_incomplete_dlc_is_not_usable(self):
        installed = [{
            "name": "Siebla-PDF", "status": "不完整",
            "version": "1.0", "detail": "缺少分卷：Siebla-PDF_03.zip",
        }]
        with patch.object(capabilities, "list_installed", return_value=installed):
            description = capabilities.describe_environment()
        self.assertIn("Siebla-PDF：不完整", description)
        self.assertIn("不要依赖此 DLC", description)
        self.assertNotIn("可尝试的任务：PDF", description)


if __name__ == "__main__":
    unittest.main()
