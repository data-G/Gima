import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GcpDeployTests(unittest.TestCase):
    def test_cloud_run_files_exist(self):
        self.assertTrue((ROOT / "Dockerfile").exists())
        self.assertTrue((ROOT / "cloudbuild.yaml").exists())
        self.assertTrue((ROOT / "config.cloud.json").exists())
        self.assertTrue((ROOT / "scripts" / "gcp_deploy_gima.sh").exists())
        self.assertTrue((ROOT / "docs" / "GCP_DEPLOY.md").exists())

    def test_dockerfile_runs_gima_on_cloud_run_port(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python -m human_ai.gima --config config.cloud.json web", dockerfile)
        self.assertIn("--host 0.0.0.0", dockerfile)
        self.assertIn("--port ${PORT:-8080}", dockerfile)

    def test_cloud_config_is_safe_for_cloud_run(self):
        config = json.loads((ROOT / "config.cloud.json").read_text(encoding="utf-8"))
        self.assertEqual(config["workspace"], "/app")
        self.assertEqual(config["data_dir"], "/tmp/gima-data")
        self.assertFalse(config["model"]["enabled"])
        self.assertFalse(config["tools"]["enabled"])
        self.assertTrue(config["teacher_models"]["free_quota_mode"])
        self.assertEqual(config["teacher_models"]["openrouter_model"], "openai/gpt-5.5")

    def test_deploy_script_is_executable_and_enables_cloud_run(self):
        script_path = ROOT / "scripts" / "gcp_deploy_gima.sh"
        script = script_path.read_text(encoding="utf-8")
        self.assertTrue(os.access(script_path, os.X_OK))
        self.assertIn("gcloud projects create", script)
        self.assertIn("cloudbuild.googleapis.com", script)
        self.assertIn("run.googleapis.com", script)
        self.assertIn("gcloud builds submit", script)


if __name__ == "__main__":
    unittest.main()
