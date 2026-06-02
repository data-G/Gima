import tempfile
import unittest
from pathlib import Path

from human_ai.readers import read_file


class ReaderTests(unittest.TestCase):
    def test_text_file_is_chunked_and_categorized(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "demo.py"
            path.write_text("print('hello')\n", encoding="utf-8")
            records = read_file(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].category, "code")
        self.assertIn("hello", records[0].content)

    def test_csv_file_is_read_as_structured_text(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "facts.csv"
            path.write_text("title,category\nDoor,vision\n", encoding="utf-8")
            records = read_file(path)
        self.assertIn("title, category", records[0].content)


if __name__ == "__main__":
    unittest.main()

