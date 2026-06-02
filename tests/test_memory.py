import csv
import tempfile
import unittest
from pathlib import Path

from human_ai.memory import MemoryStore, Record


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = MemoryStore(Path(self.temp.name))
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_add_search_and_rebuild(self):
        self.store.add(
            Record(
                category="vision",
                title="Front door event",
                content="A delivery package appeared near the front door.",
                keywords="package camera",
            )
        )
        self.assertEqual(self.store.search("package")[0]["category"], "vision")
        self.assertEqual(self.store.rebuild_index(), 1)
        self.assertEqual(self.store.search("delivery")[0]["title"], "Front door event")

    def test_duplicate_content_is_not_written_twice(self):
        record = Record(category="files", title="Note", content="Repeated content")
        self.store.add(record)
        duplicate = Record(category="files", title="Note", content="Repeated content")
        self.store.add(duplicate)
        with self.store.knowledge_path.open(newline="", encoding="utf-8") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 1)
        self.assertEqual(len(self.store.search("Repeated")), 1)

    def test_category_filter(self):
        self.store.add(Record(category="code", title="Python", content="factory pattern"))
        self.store.add(Record(category="research", title="Patterns", content="factory pattern"))
        rows = self.store.search("factory", category="code")
        self.assertEqual([row["category"] for row in rows], ["code"])

    def test_review_record_can_be_approved(self):
        record = Record(category="research", title="Draft fact", content="review me", status="review")
        self.store.add(record)
        self.assertEqual(self.store.search("review"), [])
        self.assertEqual(self.store.list_by_status("review")[0]["id"], record.id)
        self.assertTrue(self.store.update_status(record.id, "active"))
        self.assertEqual(self.store.search("review")[0]["id"], record.id)

    def test_replace_source_archives_stale_chunks(self):
        source = "/tmp/note.txt"
        self.store.replace_source(
            source,
            [Record(category="files", title="Note", content="old wording", source=source)],
        )
        self.store.replace_source(
            source,
            [Record(category="files", title="Note", content="new wording", source=source)],
        )
        self.assertEqual(self.store.search("old"), [])
        self.assertEqual(self.store.search("new")[0]["content"], "new wording")

    def test_conversation_is_written_and_searchable(self):
        self.store.append_conversation("session_1", "user", "Remember the blue umbrella")
        rows = self.store.search_conversations("umbrella")
        self.assertEqual(rows[0]["session_id"], "session_1")
        self.assertEqual(rows[0]["role"], "user")

    def test_old_conversation_csv_schema_is_migrated(self):
        self.store.conversations_path.write_text(
            "timestamp,session_id,role,message,category,importance\n"
            "2026-06-02T10:00:00+09:00,legacy,user,old message,conversation,0.50\n",
            encoding="utf-8",
        )
        self.store.rebuild_index()
        rows = self.store.search_conversations("old")
        self.assertEqual(rows[0]["session_id"], "legacy")
        with self.store.conversations_path.open(newline="", encoding="utf-8") as handle:
            self.assertEqual(next(csv.reader(handle))[0], "id")


if __name__ == "__main__":
    unittest.main()
