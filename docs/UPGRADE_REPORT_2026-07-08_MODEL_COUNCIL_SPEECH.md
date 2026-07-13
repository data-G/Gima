# Gima Upgrade Report - 2026-07-08

## Improvement chosen

Model Council planner plus OpenRouter/Microsoft MAI Voice 2 speech adapter.

## Summary

Gima now has a local model-selection council that scores several model routes for a request before spending cloud calls. It includes:

- Current configured local model.
- Installed QVAC Llama 3.2 1B GGUF at `/Users/gimhangunarathne/.qvac/models/f2bade0bc5cd4a8c_Llama-3.2-1B-Instruct-Q4_0.gguf`.
- Qwythos 9B Claude Mythos GGUF as a candidate model to review/download.
- OpenRouter selected model and fallback pool.
- Microsoft MAI Voice 2 for text-to-speech.
- OpenRouter STT and multimodal/video routes.

Gima also now has an OpenRouter speech generator for `microsoft/mai-voice-2` using `/api/v1/audio/speech`, with Azure style options and MP3/PCM output.

## Why it matters

Gima should not assume one model is best for every task. A small local model can be fast and private, while OpenRouter models can handle stronger reasoning, vision, speech, or video when the user allows cloud access. The council makes that routing visible and reviewable.

## Files changed

- `human_ai/model_council.py`
- `human_ai/services.py`
- `human_ai/web_ui.py`
- `tests/test_services.py`
- `tests/test_web_ui.py`
- `docs/UPGRADE_REPORT_2026-07-08_MODEL_COUNCIL_SPEECH.md`

## Verification results

- Python compile passed for the changed modules and tests.
- Focused model council and speech adapter tests passed.
- Focused web dashboard endpoint test passed.
- Broader web/service regression run passed: 70 tests, with 1 skipped.

## Safety defaults

- The council is local planning logic and does not call cloud models.
- MAI speech generation requires explicit consent.
- MAI speech generation requires `CLOUD_ALLOWED=true`.
- API keys are read from environment/secrets only; no key is written into source code or docs.
- Generated speech outputs include a provenance manifest.

## Next recommended upgrade

Add an approval-gated live council mode where local and cloud models each produce short candidate answers, then a judge model selects the final answer with logged cost, latency, and source notes.
