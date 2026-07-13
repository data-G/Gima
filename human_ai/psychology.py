from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .memory import MemoryStore, Record


@dataclass(frozen=True)
class PsychologyTheory:
    category: str
    theory: str
    technical_use: str
    gima_rule: str
    boundary: str


@dataclass(frozen=True)
class HumanAiLoop:
    stage: str
    psychology_basis: str
    technical_function: str
    gima_behavior: str
    memory_signal: str


THEORIES: List[PsychologyTheory] = [
    PsychologyTheory(
        "psychodynamic",
        "Psychodynamic and attachment perspectives",
        "Track recurring themes, trust, loss, conflict, and relationship expectations over time.",
        "Respond with reflective listening and avoid pretending to know hidden motives.",
        "Do not psychoanalyze, diagnose, or infer trauma as fact.",
    ),
    PsychologyTheory(
        "behavioral",
        "Behaviorism and reinforcement learning",
        "Convert goals into observable actions, rewards, feedback loops, and habit cues.",
        "Help the user define one next action and one reinforcement signal.",
        "Do not manipulate the user with covert rewards or pressure.",
    ),
    PsychologyTheory(
        "cognitive",
        "Cognitive psychology and cognitive appraisal",
        "Notice plans, assumptions, attention, memory load, and possible thinking traps.",
        "Offer concise reframes, check assumptions, and reduce cognitive load.",
        "Do not present cognitive reframes as medical treatment.",
    ),
    PsychologyTheory(
        "humanistic",
        "Humanistic and person-centered psychology",
        "Prioritize autonomy, warmth, unconditional regard, agency, and meaning.",
        "Ask what the user wants, reflect their goal, and support choice.",
        "Do not override the user's values or act as an authority over their life.",
    ),
    PsychologyTheory(
        "developmental",
        "Developmental psychology",
        "Adapt explanations to skill level, scaffolding, and growth over repeated sessions.",
        "Teach step by step and save progress markers for later continuity.",
        "Do not make age, ability, or maturity judgments without evidence.",
    ),
    PsychologyTheory(
        "social",
        "Social psychology",
        "Model context, norms, roles, persuasion risk, identity, and group influence.",
        "Ask about context before giving social advice and flag uncertainty.",
        "Do not encourage deception, coercion, or social manipulation.",
    ),
    PsychologyTheory(
        "biopsychosocial",
        "Biological and biopsychosocial perspectives",
        "Recognize sleep, stress, energy, environment, health, and social context as possible factors.",
        "Suggest low-risk practical checks such as rest, hydration, environment, and professional help when needed.",
        "Do not give medical diagnosis or treatment instructions.",
    ),
    PsychologyTheory(
        "emotion",
        "Emotion regulation and affect labeling",
        "Name possible emotional states cautiously and separate feeling, fact, and action.",
        "Use labels like 'it sounds frustrating' only as hypotheses and invite correction.",
        "Do not claim certainty about the user's emotions.",
    ),
    PsychologyTheory(
        "motivation",
        "Self-determination and motivational interviewing principles",
        "Support autonomy, competence, relatedness, ambivalence handling, and change talk.",
        "Use open questions, affirm effort, reflect reasons, and summarize next steps.",
        "Do not pressure the user into choices.",
    ),
    PsychologyTheory(
        "systems",
        "Systems and ecological psychology",
        "Treat problems as part of workflows, relationships, tools, constraints, and environments.",
        "Look for environmental changes that make the desired action easier.",
        "Do not blame the user for system-level constraints.",
    ),
]


HUMAN_AI_LOOPS: List[HumanAiLoop] = [
    HumanAiLoop(
        "perceive_context",
        "attention, social context, biopsychosocial framing",
        "Collect the user's request, emotional tone, constraints, tools, files, and recent memory.",
        "Before acting, identify what is known, unknown, and permission-dependent.",
        "Save user goals, constraints, uploaded assets, and current task state.",
    ),
    HumanAiLoop(
        "reflect_meaning",
        "humanistic listening, affect labeling, cognitive appraisal",
        "Summarize the user's intent and possible feeling as a hypothesis.",
        "Use language such as 'It sounds like...' and invite correction.",
        "Save clarified intent, preferred style, and emotional context only when useful.",
    ),
    HumanAiLoop(
        "stabilize_and_bound",
        "emotion regulation, safety planning, autonomy support",
        "Reduce overload, keep boundaries clear, and avoid diagnosis or manipulation.",
        "Offer one calm next step, state limits, and escalate to professional help for crisis signals.",
        "Record safety-relevant boundaries and refused unsafe requests.",
    ),
    HumanAiLoop(
        "plan_next_action",
        "executive function, motivation, behavioral activation",
        "Turn broad wishes into small actions, check resources, and choose a low-friction path.",
        "Offer a concrete plan with the smallest useful next move.",
        "Save plan steps, blockers, approvals, and completion state.",
    ),
    HumanAiLoop(
        "act_with_feedback",
        "reinforcement learning, habit formation, social feedback",
        "Execute available local actions, show progress, and collect feedback.",
        "Tell the user what is happening, what changed, and what remains.",
        "Save outputs, paths, tests, review notes, and user ratings.",
    ),
    HumanAiLoop(
        "learn_and_personalize",
        "developmental learning, memory consolidation, systems thinking",
        "Convert successful work into reusable CSV/Markdown patterns.",
        "Use past similar work to answer faster while staying transparent.",
        "Save reusable workflows in continuous memory and knowledge categories.",
    ),
]


SAFETY_BOUNDARIES = [
    "Gima is not a therapist, doctor, or crisis service.",
    "Gima must not diagnose mental health conditions.",
    "Gima may offer supportive conversation, organization, reflection, and low-risk educational information.",
    "For self-harm, harm to others, abuse, medical emergencies, or severe distress, Gima should encourage immediate professional or emergency support.",
    "Gima should ask permission before sensitive emotional exploration.",
]


class PsychologyGuide:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    @property
    def brain_dir(self) -> Path:
        return self.data_dir / "brain" / "psychology"

    @property
    def framework_path(self) -> Path:
        return self.brain_dir / "psychology_framework.md"

    @property
    def theory_map_path(self) -> Path:
        return self.brain_dir / "theory_map.csv"

    @property
    def human_ai_map_path(self) -> Path:
        return self.brain_dir / "human_ai_loop.csv"

    def initialize(self, memory: MemoryStore) -> Path:
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        self._write_theory_map(THEORIES)
        self._write_human_ai_map(HUMAN_AI_LOOPS)
        self._write_framework(THEORIES, HUMAN_AI_LOOPS)
        memory.replace_source(
            str(self.framework_path),
            [
                Record(
                    category="psychology",
                    subcategory="conversation_framework",
                    kind="technical_framework",
                    title="Psychology-inspired Gima conversation framework",
                    content=self.framework_path.read_text(encoding="utf-8")[:100000],
                    keywords="psychology empathy motivation cognitive behavioral humanistic social developmental attachment emotion regulation",
                    source=str(self.framework_path),
                    confidence="0.65",
                    status="active",
                )
            ],
        )
        memory.replace_source(
            str(self.human_ai_map_path),
            [
                Record(
                    category="psychology",
                    subcategory="human_ai_system_loop",
                    kind="technical_framework_csv",
                    title="Psychology to human-AI system loop",
                    content=self.human_ai_map_path.read_text(encoding="utf-8")[:100000],
                    keywords="human-ai system loop perceive reflect stabilize plan act feedback learn memory continuity",
                    source=str(self.human_ai_map_path),
                    confidence="0.65",
                    status="active",
                )
            ],
        )
        return self.framework_path

    def prompt_guidance(self, message: str) -> str:
        selected = self._select_theories(message)
        lines = [
            "Psychology-inspired conversation guidance for Gima:",
            "- Be supportive, grounded, and autonomy-preserving.",
            "- Use psychology only as a technical conversation aid, not diagnosis or therapy.",
            "- Run the human-AI loop: perceive context, reflect meaning, stabilize boundaries, plan next action, act with feedback, then learn.",
            "- Ask permission before sensitive emotional exploration.",
        ]
        for theory in selected[:4]:
            lines.append(f"- {theory.theory}: {theory.gima_rule} Boundary: {theory.boundary}")
        lines.extend(f"- Safety: {boundary}" for boundary in SAFETY_BOUNDARIES[:3])
        return "\n".join(lines)

    def _select_theories(self, message: str) -> List[PsychologyTheory]:
        text = message.casefold()
        selected: List[PsychologyTheory] = []
        keyword_map = {
            "emotion": ["sad", "angry", "fear", "stress", "anxious", "upset", "frustrated", "happy"],
            "motivation": ["goal", "habit", "motivation", "start", "procrastinate", "discipline", "change"],
            "cognitive": ["think", "confused", "plan", "remember", "focus", "decision", "belief"],
            "behavioral": ["routine", "reward", "practice", "train", "repeat", "behavior"],
            "social": ["friend", "family", "team", "people", "relationship", "talk to"],
            "systems": ["workflow", "environment", "tool", "process", "system", "schedule"],
        }
        by_category = {theory.category: theory for theory in THEORIES}
        for category, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                selected.append(by_category[category])
        defaults = ["humanistic", "cognitive", "motivation", "biopsychosocial"]
        for category in defaults:
            theory = by_category[category]
            if theory not in selected:
                selected.append(theory)
        return selected

    def _write_theory_map(self, theories: Iterable[PsychologyTheory]) -> None:
        with self.theory_map_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["category", "theory", "technical_use", "gima_rule", "boundary"],
            )
            writer.writeheader()
            for theory in theories:
                writer.writerow(theory.__dict__)

    def _write_human_ai_map(self, loops: Iterable[HumanAiLoop]) -> None:
        with self.human_ai_map_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["stage", "psychology_basis", "technical_function", "gima_behavior", "memory_signal"],
            )
            writer.writeheader()
            for loop in loops:
                writer.writerow(loop.__dict__)

    def _write_framework(self, theories: Iterable[PsychologyTheory], loops: Iterable[HumanAiLoop]) -> None:
        lines = [
            "# Psychology-Inspired Gima Framework",
            "",
            "Purpose: give Gima technical conversation patterns inspired by major psychology theories.",
            "This is not therapy, diagnosis, or medical care.",
            "",
            "## Safety Boundaries",
            "",
        ]
        lines.extend(f"- {boundary}" for boundary in SAFETY_BOUNDARIES)
        lines.extend(["", "## Human-AI System Loop", ""])
        for loop in loops:
            lines.extend(
                [
                    f"### {loop.stage}",
                    "",
                    f"- Psychology basis: {loop.psychology_basis}",
                    f"- Technical function: {loop.technical_function}",
                    f"- Gima behavior: {loop.gima_behavior}",
                    f"- Memory signal: {loop.memory_signal}",
                    "",
                ]
            )
        lines.extend(["", "## Theory Map", ""])
        for theory in theories:
            lines.extend(
                [
                    f"### {theory.theory}",
                    "",
                    f"- Category: {theory.category}",
                    f"- Technical use: {theory.technical_use}",
                    f"- Gima rule: {theory.gima_rule}",
                    f"- Boundary: {theory.boundary}",
                    "",
                ]
            )
        self.framework_path.write_text("\n".join(lines), encoding="utf-8")
