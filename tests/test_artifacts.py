import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from human_ai.artifacts import ChatArtifactEngine


class ChatArtifactEngineTests(unittest.TestCase):
    def test_misspelled_seeni_sambol_budget_routes_to_verified_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "catering_budget" / "seeni_sambol_budget_7000"
            project.mkdir(parents=True)
            for suffix in ("xlsx", "jpg", "pdf"):
                (project / f"seeni_sambol_sandwich_budget_7000.{suffix}").write_bytes(b"test")

            answer = ChatArtifactEngine(root, []).answer(
                "make seeni symbol sandwitched 7000 to give budget"
            )

            self.assertIsNotNone(answer)
            self.assertIn("Rs 721,382", answer.reply)
            self.assertEqual(len(answer.files), 3)
            self.assertEqual({file["name"].split(".")[-1] for file in answer.files}, {"xlsx", "jpg", "pdf"})

    def test_unrelated_chat_does_not_trigger_catering_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            answer = ChatArtifactEngine(Path(temp), []).answer("tell me about psychology")
            self.assertIsNone(answer)

    def test_chicken_costing_request_parses_quantity_and_returns_three_formats(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            def fake_builder(model_path, stem):
                paths = [model_path.parent / f"{stem}.{suffix}" for suffix in ("xlsx", "jpg", "pdf")]
                for path in paths:
                    path.write_bytes(b"test")
                return paths

            with patch("human_ai.artifacts._build_catering_files", side_effect=fake_builder):
                answer = ChatArtifactEngine(root, []).answer(
                    "Create a researched costing table for 2,000 chicken sandwiches and provide Excel, JPG and PDF."
                )

            self.assertIsNotNone(answer)
            self.assertIn("2,000", answer.reply)
            self.assertIn("Rs 457,829", answer.reply)
            self.assertEqual(len(answer.files), 3)

    def test_ambiguous_japan_matches_request_asks_for_sport_without_fake_files(self):
        with tempfile.TemporaryDirectory() as temp:
            answer = ChatArtifactEngine(Path(temp), []).answer(
                "make a table of japan vs other countries matches and time japan time"
            )
        self.assertIsNotNone(answer)
        self.assertIn("need the sport or competition", answer.reply)
        self.assertIn("did not create placeholder files", answer.reply)
        self.assertEqual(answer.files, [])
        self.assertFalse(answer.used_internet)

    def test_current_sports_schedule_automatically_researches_web(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = ChatArtifactEngine(Path(temp), [])
            with patch.object(engine.importer, "search", return_value=["https://example.com/japan-football"]), patch.object(
                engine.importer,
                "fetch",
                return_value="Japan football fixtures. Japan v Example, 20:00 JST.",
            ):
                answer = engine.answer("make a table of upcoming Japan football matches in Japan time")
        self.assertIsNotNone(answer)
        self.assertTrue(answer.used_internet)
        self.assertEqual(answer.sources, ["https://example.com/japan-football"])
        self.assertTrue(any(file["name"].endswith(".pdf") for file in answer.files))

    def test_look_up_request_routes_to_web_search(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = ChatArtifactEngine(Path(temp), [])
            with patch.object(engine.importer, "search", return_value=["https://example.com/current-ai"]), patch.object(
                engine.importer,
                "fetch",
                return_value="Current AI systems can search, cite, use tools, and create artifacts.",
            ):
                answer = engine.answer("look up current AI browser tool capabilities")
        self.assertIsNotNone(answer)
        self.assertTrue(answer.used_internet)
        self.assertIn("I searched public web sources", answer.reply)
        self.assertEqual(answer.sources, ["https://example.com/current-ai"])

    def test_web_search_strips_nul_bytes_before_writing_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            engine = ChatArtifactEngine(root, [])
            with patch.object(engine.importer, "search", return_value=["https://example.com/nul"]), patch.object(
                engine.importer,
                "fetch",
                return_value="Current\x00 AI systems can search, cite, use tools, and create artifacts.",
            ):
                answer = engine.answer("search internet current AI systems")
            self.assertIsNotNone(answer)
            csv_file = next(Path(file["path"]) for file in answer.files if file["name"].endswith(".csv"))
            self.assertNotIn("\x00", csv_file.read_text(encoding="utf-8"))

    def test_browse_url_imports_direct_public_page(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = ChatArtifactEngine(Path(temp), [])
            with patch.object(
                engine.importer,
                "fetch",
                return_value="Gima can browse public pages, summarize them, and save source artifacts.",
            ):
                answer = engine.answer("browse https://example.com/gima")
        self.assertIsNotNone(answer)
        self.assertTrue(answer.used_internet)
        self.assertIn("I browsed this public page", answer.reply)
        self.assertEqual(answer.sources, ["https://example.com/gima"])
        self.assertEqual({file["name"] for file in answer.files}, {"web_page_source.csv", "web_page_summary.md"})

    def test_current_weather_request_uses_weather_source(self):
        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(self.body).encode("utf-8")

        responses = [
            Response({"results": [{"name": "Osaka", "country": "Japan", "latitude": 34.69379, "longitude": 135.50107}]}),
            Response(
                {
                    "current": {
                        "time": "2026-07-03T12:00",
                        "temperature_2m": 29,
                        "apparent_temperature": 33,
                        "relative_humidity_2m": 70,
                        "wind_speed_10m": 12,
                        "precipitation": 0,
                        "weather_code": 2,
                    }
                }
            ),
        ]

        with tempfile.TemporaryDirectory() as temp, patch("urllib.request.urlopen", side_effect=responses):
            answer = ChatArtifactEngine(Path(temp), []).answer("Gima, search the web for current weather in Osaka.")
        self.assertIsNotNone(answer)
        self.assertTrue(answer.used_internet)
        self.assertIn("Current weather for **Osaka, Japan**", answer.reply)
        self.assertIn("29°C", answer.reply)
        self.assertEqual({file["name"] for file in answer.files}, {"current_weather.csv", "current_weather.md"})

    def test_generic_table_request_does_not_generate_prompt_only_report(self):
        with tempfile.TemporaryDirectory() as temp:
            answer = ChatArtifactEngine(Path(temp), []).answer("make a table")
        self.assertIsNotNone(answer)
        self.assertIn("does not identify a trustworthy dataset", answer.reply)
        self.assertEqual(answer.files, [])


if __name__ == "__main__":
    unittest.main()
