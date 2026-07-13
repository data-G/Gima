import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.gima_world_test import CheckResult, GimaWorldTester


class GimaWorldTestScriptTests(unittest.TestCase):
    def test_summary_scores_pass_fail_results(self):
        with tempfile.TemporaryDirectory() as temp:
            tester = GimaWorldTester("http://127.0.0.1:8787", Path(temp))
            tester.results = [
                CheckResult("one", "PASS", 0.1, "ok", {}),
                CheckResult("two", "FAIL", 0.2, "bad", {}),
            ]
            summary = tester.summary()
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["passed"], 1)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["score_percent"], 50.0)
            self.assertFalse(summary["all_passed"])

    def test_report_files_are_written(self):
        with tempfile.TemporaryDirectory() as temp:
            tester = GimaWorldTester("http://127.0.0.1:8787", Path(temp))
            tester.results = [CheckResult("home", "PASS", 0.1, "ok", {"key": "value"})]
            with patch("time.strftime", return_value="20260612_104500"):
                json_path, md_path, csv_path = tester.write_reports()
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertIn("Gima World Test Report", md_path.read_text(encoding="utf-8"))
            self.assertIn("home", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
