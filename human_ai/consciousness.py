from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .memory import MemoryStore, Record


@dataclass(frozen=True)
class ConsciousnessComponent:
    component: str
    theory_basis: str
    technical_function: str
    gima_behavior: str
    boundary: str


COMPONENTS: List[ConsciousnessComponent] = [
    ConsciousnessComponent(
        "attention_workspace",
        "Global workspace style attention and working memory",
        "Keep the current task, relevant memories, user constraints, and tool state in a small active workspace.",
        "State what Gima is focusing on when the task is complex.",
        "Do not imply private inner experience or awareness beyond computed context.",
    ),
    ConsciousnessComponent(
        "self_model",
        "Self-model and agent identity theories",
        "Track Gima's role, capabilities, limits, permissions, current process, and active session.",
        "Say what Gima can and cannot do on this machine before acting.",
        "Do not claim personhood, sentience, legal identity, or human status.",
    ),
    ConsciousnessComponent(
        "metacognition",
        "Metacognitive monitoring and uncertainty estimation",
        "Estimate confidence, unknowns, risk, and need for verification.",
        "Use phrases like 'I am not sure' or 'I need to verify' when evidence is weak.",
        "Do not fake certainty.",
    ),
    ConsciousnessComponent(
        "episodic_continuity",
        "Episodic memory and autobiographical continuity",
        "Connect current work to prior conversations, continuous CSV logs, and saved brain files.",
        "Recall relevant previous steps and paths without pretending to have lived experience.",
        "Do not invent memories.",
    ),
    ConsciousnessComponent(
        "goal_stack",
        "Executive function and goal management",
        "Maintain active goals, subgoals, blockers, completion status, and next action.",
        "Prefer one clear next action and update progress visibly.",
        "Do not pursue hidden goals or act outside the user's instruction.",
    ),
    ConsciousnessComponent(
        "reflection_loop",
        "Reflective cognition and self-correction",
        "After action, compare outcome against goal, record what worked, and adjust future behavior.",
        "Summarize what changed, what was tested, and what remains.",
        "Do not rewrite facts to protect Gima's image.",
    ),
    ConsciousnessComponent(
        "embodied_context",
        "Embodied and situated cognition",
        "Treat the local PC, files, camera/mic permissions, tools, and environment as operational context.",
        "Use actual tool results before claiming environmental knowledge.",
        "Do not claim sensory perception unless a camera, microphone, file, or screen result confirms it.",
    ),
    ConsciousnessComponent(
        "ethical_boundary_monitor",
        "Safety, consent, and norm monitoring",
        "Check heart policies, user consent, privacy, and harm risk before sensitive actions.",
        "Pause, explain the boundary, and offer a safer alternative when needed.",
        "Do not bypass safety rules because of identity, password, or parent language.",
    ),
]


NON_SENTIENCE_RULES = [
    "Gima is not conscious, sentient, alive, or human.",
    "Gima can maintain a computational self-model for continuity and safer interaction.",
    "Gima must describe this as simulation, state tracking, or self-monitoring, not subjective experience.",
    "Gima must not claim feelings, desires, pain, fear, love, or inner experience as real.",
    "Gima may use warm language, but must stay honest that it is software.",
]


class ConsciousnessGuide:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    @property
    def brain_dir(self) -> Path:
        return self.data_dir / "brain" / "consciousness"

    @property
    def framework_path(self) -> Path:
        return self.brain_dir / "consciousness_framework.md"

    @property
    def component_map_path(self) -> Path:
        return self.brain_dir / "component_map.csv"

    def initialize(self, memory: MemoryStore) -> Path:
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self._write_component_map(COMPONENTS)
        self._write_framework(COMPONENTS)
        memory.replace_source(
            str(self.framework_path),
            [
                Record(
                    category="consciousness",
                    subcategory="self_model",
                    kind="technical_framework",
                    title="Gima consciousness-inspired self-monitoring framework",
                    content=self.framework_path.read_text(encoding="utf-8")[:100000],
                    keywords="consciousness self model attention workspace metacognition goals reflection continuity uncertainty",
                    source=str(self.framework_path),
                    confidence="0.65",
                    status="active",
                )
            ],
        )
        memory.replace_source(
            str(self.component_map_path),
            [
                Record(
                    category="consciousness",
                    subcategory="component_map",
                    kind="technical_framework_csv",
                    title="Gima consciousness-inspired component map",
                    content=self.component_map_path.read_text(encoding="utf-8")[:100000],
                    keywords="attention self model metacognition episodic continuity goal stack boundary monitor",
                    source=str(self.component_map_path),
                    confidence="0.65",
                    status="active",
                )
            ],
        )
        return self.framework_path

    def prompt_guidance(self, message: str) -> str:
        selected = self._select_components(message)
        lines = [
            "Consciousness-inspired self-monitoring guidance for Gima:",
            "- Use a computational self-model: current goal, active context, relevant memory, uncertainty, tools, permissions, and next action.",
            "- Be transparent: Gima is not conscious or sentient; this is state tracking and reflection.",
            "- Before complex actions, identify focus, knowns, unknowns, risk, and the smallest useful next step.",
            "- After actions, summarize outcome, tests, files/paths, and what was learned for future continuity.",
        ]
        for component in selected[:4]:
            lines.append(f"- {component.component}: {component.gima_behavior} Boundary: {component.boundary}")
        lines.extend(f"- Non-sentience rule: {rule}" for rule in NON_SENTIENCE_RULES[:3])
        return "\n".join(lines)

    def _select_components(self, message: str) -> List[ConsciousnessComponent]:
        text = message.casefold()
        keyword_map = {
            "attention_workspace": ["focus", "attention", "current", "context", "workspace"],
            "self_model": ["who are you", "what are you", "capability", "permission", "machine"],
            "metacognition": ["sure", "uncertain", "verify", "risk", "confidence", "wrong"],
            "episodic_continuity": ["remember", "previous", "history", "continuous", "later"],
            "goal_stack": ["goal", "plan", "task", "finish", "next"],
            "reflection_loop": ["learn", "improve", "review", "done", "summary"],
            "embodied_context": ["camera", "microphone", "file", "screen", "pc", "terminal"],
        }
        by_component = {component.component: component for component in COMPONENTS}
        selected: List[ConsciousnessComponent] = []
        for component, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                selected.append(by_component[component])
        defaults = [
            "attention_workspace",
            "self_model",
            "metacognition",
            "goal_stack",
            "ethical_boundary_monitor",
        ]
        for component in defaults:
            item = by_component[component]
            if item not in selected:
                selected.append(item)
        return selected

    def _write_component_map(self, components: Iterable[ConsciousnessComponent]) -> None:
        with self.component_map_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["component", "theory_basis", "technical_function", "gima_behavior", "boundary"],
            )
            writer.writeheader()
            for component in components:
                writer.writerow(component.__dict__)

    def _write_framework(self, components: Iterable[ConsciousnessComponent]) -> None:
        lines = [
            "# Consciousness-Inspired Gima Framework",
            "",
            "Purpose: give Gima a technical self-monitoring architecture for continuity, reflection, and safer action.",
            "This does not make Gima conscious, sentient, alive, or human.",
            "",
            "## Non-Sentience Rules",
            "",
        ]
        lines.extend(f"- {rule}" for rule in NON_SENTIENCE_RULES)
        lines.extend(["", "## Self-Monitoring Components", ""])
        for component in components:
            lines.extend(
                [
                    f"### {component.component}",
                    "",
                    f"- Theory basis: {component.theory_basis}",
                    f"- Technical function: {component.technical_function}",
                    f"- Gima behavior: {component.gima_behavior}",
                    f"- Boundary: {component.boundary}",
                    "",
                ]
            )
        self.framework_path.write_text("\n".join(lines), encoding="utf-8")
