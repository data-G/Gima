import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from human_ai import gima


class GimaControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp.name) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "workspace": self.temp.name,
                    "data_dir": ".human-ai",
                    "model": {"enabled": False},
                    "permissions": {"require_scoped_grants": False},
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def run_gima(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = gima.main(["--config", str(self.config_path), *args])
        self.assertEqual(code, 0)
        return output.getvalue()

    def test_remember_and_search(self):
        remember = self.run_gima("remember", "Goal", "Build", "the", "best", "Gima")
        self.assertIn("Remembered as", remember)
        search = self.run_gima("search", "best Gima")
        self.assertIn("Goal", search)

    def test_status_prints_control_center_summary(self):
        with patch("human_ai.gima.BrainServer.status") as status:
            status.return_value = {"running": False, "pid": None, "models": None}
            output = self.run_gima("status")
        self.assertIn("Gima config:", output)
        self.assertIn("Brain: stopped", output)


if __name__ == "__main__":
    unittest.main()
