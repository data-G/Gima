import unittest

from human_ai.free_llm_planner import free_llm_matrix, free_llm_plan


class FreeLlmPlannerTests(unittest.TestCase):
    def test_speed_task_prefers_groq(self):
        plan = free_llm_plan("fast voice realtime chat", privacy="balanced", limit=3)
        names = [row["name"] for row in plan["recommendations"]]
        self.assertIn("Groq", names[:2])
        groq = next(row for row in plan["recommendations"] if row["name"] == "Groq")
        self.assertTrue(any("speed" in reason or "latency" in reason for reason in groq["reasons"]))

    def test_strict_privacy_penalizes_training_opt_in(self):
        plan = free_llm_plan("long private company document analysis", privacy="strict", limit=20)
        mistral = next(row for row in plan["recommendations"] if row["name"] == "Mistral Experiment")
        google = next(row for row in plan["recommendations"] if row["name"] == "Google AI Studio")
        openrouter = next(row for row in plan["recommendations"] if row["name"] == "OpenRouter")
        self.assertLess(mistral["score"], openrouter["score"])
        self.assertLess(google["score"], openrouter["score"])
        self.assertTrue(any("privacy penalty" in reason for reason in google["reasons"]))

    def test_matrix_contains_openrouter_source_data(self):
        rows = free_llm_matrix()
        openrouter = next(row for row in rows if row["provider_id"] == "openrouter")
        self.assertEqual(openrouter["openai_compatible"], "Yes")
        self.assertIn("20+", openrouter["free_models"])
        self.assertGreaterEqual(len(rows), 13)
        self.assertIn("cohere", {row["provider_id"] for row in rows})
        self.assertIn("vercel_ai_gateway", {row["provider_id"] for row in rows})
        for row in rows:
            self.assertTrue(all(len(risk) > 3 for risk in row["risks"]))


if __name__ == "__main__":
    unittest.main()
