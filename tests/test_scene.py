import json
import tempfile
import unittest
from pathlib import Path

from human_ai.memory import MemoryStore
from human_ai.scene import SceneObservation, parse_detections, save_observation


class SceneTests(unittest.TestCase):
    def test_parse_detections_counts_only_people_above_threshold(self):
        detections = parse_detections(
            {
                "detections": [
                    {"label": "person", "confidence": 0.91, "box": [1, 2, 3, 4]},
                    {"label": "dog", "confidence": 0.99, "box": [4, 5, 6, 7]},
                    {"label": "person", "confidence": 0.20, "box": [7, 8, 9, 10]},
                    {"class": "PERSON", "score": 0.88, "bbox": [10, 11, 12, 13]},
                ]
            }
        )
        self.assertEqual(len(detections), 2)

    def test_scene_summary_handles_group(self):
        observation = SceneObservation("front_camera", Path("/tmp/frame.jpg"), 4, [])
        self.assertEqual(observation.summary, "4 people are visible near front_camera.")

    def test_save_observation_indexes_anonymous_count(self):
        with tempfile.TemporaryDirectory() as temp:
            store = MemoryStore(Path(temp))
            observation = SceneObservation("webcam", Path("/tmp/frame.jpg"), 2, [])
            record_id = save_observation(store, observation)
            row = store.search("people")[0]
        self.assertEqual(row["id"], record_id)
        self.assertIn('"people_count": 2', row["content"])


if __name__ == "__main__":
    unittest.main()
