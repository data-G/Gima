import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.system_doctor import (
    build_daily_improvement_plan,
    build_area_agent_supervisor,
    build_ai_era_requirements,
    build_doctor_report,
    build_hardware_profile,
    latest_ai_era_requirements_agent,
    latest_area_agent_supervisor,
    latest_daily_improvement_agent,
    run_ai_era_requirements_agent,
    run_area_agent_supervisor,
    run_daily_improvement_agent,
    write_daily_improvement_plan,
    write_own_model_plan,
)


class SystemDoctorTests(unittest.TestCase):
    def test_hardware_profile_classifies_current_pc_strategy(self):
        with patch("human_ai.system_doctor._sysctl_int") as sysctl_int, patch(
            "human_ai.system_doctor._sysctl_text"
        ) as sysctl_text, patch("platform.machine", return_value="x86_64"):
            sysctl_int.side_effect = lambda name: {"hw.memsize": 16 * 1024**3, "hw.ncpu": 8}.get(name, 0)
            sysctl_text.side_effect = lambda name: {"machdep.cpu.brand_string": "Intel test CPU"}.get(name, "")

            profile = build_hardware_profile()

        self.assertEqual(profile.local_ai_tier, "local_small")
        self.assertIn("3B to 4B", profile.recommended_model)
        self.assertIn("4B model", profile.strategy)

    def test_doctor_report_has_checks_and_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.resolved_hands_out_dir.mkdir(parents=True, exist_ok=True)
            config.resolved_brain_csv_path.parent.mkdir(parents=True, exist_ok=True)
            config.resolved_brain_csv_path.write_text("id,title,content\n1,t,c\n", encoding="utf-8")
            config.model.active_level = "strong"
            config.model.model = "gima-local-qwen2.5-7b"
            with patch("human_ai.system_doctor.dependency_report", return_value={"llama-server": True, "ffmpeg": True, "ffprobe": True}):
                report = build_doctor_report(config, {"running": True, "ready": True, "pid": 123})

        self.assertIn("hardware", report)
        self.assertIn("readiness_score", report)
        self.assertIn("improvement_plan", report)
        self.assertIn("growth_plan", report)
        self.assertIn("hardware_upgrade_plan", report)
        self.assertIn("legal_earning_plan", report)
        self.assertIn("autonomy_boundaries", report)
        self.assertIn("daily_improvement_plan", report)
        self.assertIn("ai_era_requirements", report)
        self.assertIn("own_model_plan", report)
        self.assertEqual(report["active_level"], "strong")
        self.assertIn("7B", report["strategy"])
        self.assertTrue(any(row["phase"] == "P0 Reliability Core" for row in report["improvement_plan"]))
        self.assertTrue(any("paid work" in row["phase"] for row in report["growth_plan"]))
        self.assertTrue(any("Catering" in row["offer"] for row in report["legal_earning_plan"]))
        self.assertTrue(any("AI influencer" in row["offer"] for row in report["legal_earning_plan"]))
        self.assertTrue(any(row["area"] == "Money" for row in report["autonomy_boundaries"]))
        self.assertTrue(any(row["area"] == "Rights and client data" for row in report["autonomy_boundaries"]))
        self.assertTrue(any(row["area"] == "AI influencer identity" for row in report["autonomy_boundaries"]))
        self.assertTrue(any(stage["stage"].startswith("1.") for stage in report["own_model_plan"]["stages"]))
        self.assertTrue(any(check["name"] == "Brain server" and check["status"] == "ok" for check in report["checks"]))

    def test_daily_improvement_plan_can_be_written(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            plan = build_daily_improvement_plan(config, {"running": True, "ready": True})
            path = write_daily_improvement_plan(config, {"running": True, "ready": True})
            self.assertEqual(plan["kind"], "gima_daily_improvement_plan")
            self.assertEqual(len(plan["daily_actions"]), 6)
            self.assertTrue(path.exists())
            self.assertTrue(path.with_suffix(".md").exists())
            self.assertIn("world-class", path.read_text(encoding="utf-8"))

    def test_daily_improvement_agent_run_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            run = run_daily_improvement_agent(config, {"running": True, "ready": True})
            latest = latest_daily_improvement_agent(config)

        self.assertEqual(run["kind"], "gima_daily_improvement_agent_run")
        self.assertEqual(run["agent"], "Daily Improvement Agent")
        self.assertIn("run_path", run)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["agent"], "Daily Improvement Agent")

    def test_ai_era_requirements_agent_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            report = build_ai_era_requirements(config, {"running": True, "ready": True})
            run = run_ai_era_requirements_agent(config, {"running": True, "ready": True})
            latest = latest_ai_era_requirements_agent(config)

            brain_csv = config.resolved_brain_csv_path
            knowledge_text = (config.resolved_data_dir / "csv" / "knowledge.csv").read_text(encoding="utf-8")
            brain_csv_exists = brain_csv.exists()

            self.assertEqual(report["kind"], "gima_ai_era_requirements")
            self.assertEqual(run["agent"], "AI Era Requirements Agent")
            self.assertEqual(run["cadence"], "minute_local_check")
            self.assertIsNotNone(latest)
            self.assertTrue(any(row["name"] == "legal_growth" for row in latest["requirements"]))
            self.assertTrue(brain_csv_exists)
            self.assertIn("minute-world-ai-requirements", knowledge_text)

    def test_area_agent_supervisor_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.resolved_brain_csv_path.parent.mkdir(parents=True, exist_ok=True)
            config.resolved_brain_csv_path.write_text("id,title,content\n1,t,c\n", encoding="utf-8")
            report = build_area_agent_supervisor(config, {"running": True, "ready": True})
            run = run_area_agent_supervisor(config, {"running": True, "ready": True})
            latest = latest_area_agent_supervisor(config)

            knowledge_text = (config.resolved_data_dir / "csv" / "knowledge.csv").read_text(encoding="utf-8")

            self.assertEqual(report["kind"], "gima_area_agent_supervisor")
            self.assertEqual(run["agent"], "24/7 Area Agent Supervisor")
            self.assertGreaterEqual(run["area_count"], 10)
            self.assertIsNotNone(latest)
            self.assertTrue(any(area["name"] == "Video and media" for area in latest["areas"]))
            self.assertIn("area-agent-supervisor", knowledge_text)

    def test_own_model_plan_can_be_written(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.model.active_level = "strong"
            config.model.model = "gima-local-qwen2.5-7b"
            path = write_own_model_plan(config, {"running": True, "ready": True})

            self.assertTrue(path.exists())
            self.assertTrue(path.with_suffix(".md").exists())
            self.assertIn("Gima Own Model Plan", path.with_suffix(".md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
