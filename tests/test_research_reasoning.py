import tempfile
import unittest
from pathlib import Path

from human_ai.agent import Agent
from human_ai.config import Config
from human_ai.memory import Record
from human_ai.research_reasoning import ResearchReasoner, expand_query_terms


class ResearchReasoningTests(unittest.TestCase):
    def test_query_expansion_adds_research_terms(self):
        terms = expand_query_terms("How should Gima use RAG and reflection?")
        self.assertIn("rag", terms)
        self.assertIn("retrieval", terms)
        self.assertIn("critique", terms)
        self.assertIn("reflexion", terms)

    def test_reasoner_creates_cited_self_checked_answer_and_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp) / ".human-ai"
            reasoner = ResearchReasoner(data_dir)
            answer = reasoner.answer_from_memory(
                "How should Gima use retrieval augmented generation?",
                [
                    {
                        "id": "kb_rag",
                        "title": "RAG note",
                        "content": "Retrieval augmented generation uses external memory and source provenance to reduce hallucination.",
                        "keywords": "rag retrieval provenance memory",
                        "source": "paper://rag",
                        "status": "active",
                        "confidence": "0.8",
                    }
                ],
            )

            self.assertIsNotNone(answer)
            assert answer is not None
            self.assertIn("Research-backed answer", answer.text)
            self.assertIn("Sources:", answer.text)
            self.assertIn("Self-check:", answer.text)
            self.assertTrue((data_dir / "csv" / "research_traces.csv").exists())
            self.assertIn(answer.trace_id, (data_dir / "csv" / "research_traces.csv").read_text(encoding="utf-8"))
            self.assertTrue((data_dir / "brain" / "research_methods" / "advanced_rag_methods.md").exists())

    def test_agent_memory_fallback_uses_research_reasoning(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp), data_dir=Path(".human-ai"))
            config.model.enabled = False
            agent = Agent(config)
            agent.memory.add(
                Record(
                    category="research",
                    title="Self-RAG lesson",
                    content="Self-RAG retrieves only when useful, critiques retrieved passages, and checks generation quality.",
                    keywords="self-rag retrieval critique reflection",
                    source="https://arxiv.org/abs/2310.11511",
                )
            )

            reply = agent.chat("What does Self-RAG teach Gima about retrieval and critique?")

            self.assertIn("Research-backed answer", reply)
            self.assertIn("Self-check:", reply)
            self.assertIn("https://arxiv.org/abs/2310.11511", reply)


if __name__ == "__main__":
    unittest.main()
