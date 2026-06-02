from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import Config
from .memory import MemoryStore, Record


@dataclass
class Detection:
    label: str
    confidence: float
    box: List[float]


@dataclass
class SceneObservation:
    camera_id: str
    image_path: Path
    people_count: int
    detections: List[Detection]

    @property
    def summary(self) -> str:
        if self.people_count == 0:
            return f"No people are visible near {self.camera_id}."
        if self.people_count == 1:
            return f"One person is visible near {self.camera_id}."
        return f"{self.people_count} people are visible near {self.camera_id}."


def parse_detections(payload: Any, minimum_confidence: float = 0.50) -> List[Detection]:
    if isinstance(payload, dict):
        payload = payload.get("detections", [])
    detections: List[Detection] = []
    for item in payload:
        label = str(item.get("label", item.get("class", ""))).casefold()
        confidence = float(item.get("confidence", item.get("score", 0)))
        box = [float(value) for value in item.get("box", item.get("bbox", []))]
        if label == "person" and confidence >= minimum_confidence:
            detections.append(Detection(label, confidence, box))
    return detections


class LocalPersonDetector:
    """Run an optional local detector that prints COCO-style JSON."""

    def __init__(self, config: Config):
        self.config = config

    def detect(self, image_path: Path) -> SceneObservation:
        vision = self.config.vision
        if not vision.detector_command:
            raise RuntimeError("Person detection requires a configured local detector command")
        command = [part.replace("{image}", str(image_path.resolve())) for part in vision.detector_command]
        if all("{image}" not in part for part in vision.detector_command):
            command.append(str(image_path.resolve()))
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=120)
        detections = parse_detections(json.loads(result.stdout), vision.minimum_confidence)
        return SceneObservation(vision.camera_id, image_path.resolve(), len(detections), detections)


def save_observation(memory: MemoryStore, observation: SceneObservation) -> str:
    details: Dict[str, object] = {
        "camera_id": observation.camera_id,
        "people_count": observation.people_count,
        "detections": [
            {"label": item.label, "confidence": item.confidence, "box": item.box}
            for item in observation.detections
        ],
    }
    record_id = memory.add(
        Record(
            category="vision",
            subcategory="people_presence",
            kind="scene_observation",
            title=f"People near {observation.camera_id}: {observation.people_count}",
            content=f"{observation.summary}\n{json.dumps(details, sort_keys=True)}",
            keywords=f"camera people presence {observation.camera_id}",
            source=observation.camera_id,
            media_path=str(observation.image_path),
            confidence="0.80",
        )
    )
    memory.audit("scene_observation", observation.camera_id, observation.summary, "ok")
    return record_id
