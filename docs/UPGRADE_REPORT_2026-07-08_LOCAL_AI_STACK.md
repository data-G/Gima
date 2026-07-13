# Gima Upgrade Report - 2026-07-08

## Improvement chosen

Local AI stack planner for the user's i7-7700HQ / 16GB RAM laptop.

## Summary

Gima now turns the pasted local-AI setup table into a live planning endpoint and dashboard card. It recommends unlimited local-first tools, realistic model sizes, install order, Ollama commands, and video limitations for this laptop.

The feature writes reusable CSV, Markdown, and JSON artifacts into `hands/out/local_ai_stack`.

## Why it matters

The user wants unlimited/free AI usage where possible. On this hardware, that means using local tools for everyday chat, coding, documents, transcription, and planning, while being honest that serious image/video generation needs a suitable GPU or approved cloud backend.

## Files changed

- `human_ai/local_ai_stack.py`
- `human_ai/web_ui.py`
- `tests/test_local_ai_stack.py`
- `tests/test_web_ui.py`
- `docs/UPGRADE_REPORT_2026-07-08_LOCAL_AI_STACK.md`

## Verification results

- Python compile passed for the changed modules and tests.
- Focused local stack and web dashboard tests passed.
- Broader regression run passed: 77 tests, with 1 skipped.

## Sources checked

- LM Studio offline documentation.
- Ollama hardware support documentation.
- ComfyUI GitHub project.
- whisper.cpp GitHub project.

## Risk level

Low. This is local planning and artifact generation only. It does not install software, download large models, edit secrets, or call cloud APIs.

## Next recommended upgrade

Add an optional local installer/checker that detects whether LM Studio, Ollama, Open WebUI, Continue, ComfyUI, and whisper.cpp are installed, then shows exact next actions without auto-installing large packages.
