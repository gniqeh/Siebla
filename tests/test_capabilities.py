"""Regression tests for Siebla's dynamic AI capability handoff."""
import unittest
from unittest.mock import patch

import capabilities


class CapabilityDescriptionTests(unittest.TestCase):
    def test_no_dlc_is_not_advertised(self):
        with patch.object(capabilities, "list_installed", return_value=[]):
            description = capabilities.describe_environment()
        self.assertIn("DLC：无。", description)
        self.assertNotIn("可尝试的任务：PDF", description)
        self.assertNotIn("可尝试的任务：XLSX", description)

    def test_only_excel_does_not_imply_pdf_or_media(self):
        installed = [{
            "name": "Siebla-Excel", "status": "正常",
            "version": "1.0", "detail": "全部分卷已校验并安装",
        }]
        with patch.object(capabilities, "list_installed", return_value=installed):
            description = capabilities.describe_environment()
        self.assertIn("Siebla-Excel（已安装）", description)
        self.assertIn("pandas", description)
        self.assertNotIn("Siebla-PDF", description)
        self.assertNotIn("Siebla-Media", description)

    def test_incomplete_dlc_is_not_usable(self):
        installed = [{
            "name": "Siebla-PDF", "status": "不完整",
            "version": "1.0", "detail": "缺少分卷：Siebla-PDF_03.zip",
        }]
        with patch.object(capabilities, "list_installed", return_value=installed):
            description = capabilities.describe_environment()
        self.assertIn("Siebla-PDF（不完整，不可用）", description)
        self.assertIn("不能联网或 pip 安装新库", description)
        self.assertNotIn("可尝试的任务：PDF", description)


if __name__ == "__main__":
    unittest.main()
