# Gima Upgrade Report - 2026-07-08

## Improvement chosen

Cloud consent gating for linked AI APIs.

## Summary

Gima is local-first, but it also supports linked cloud AI providers for stronger chat, image generation, and video generation. This upgrade adds a single safety rule across the cloud paths: Gima must not send prompts or media-generation requests to external AI APIs unless `CLOUD_ALLOWED=true` is set in the runtime environment.

## Why it matters

Local-first AI should protect user data by default. API keys alone should not imply permission to transmit private prompts, attached-file context, creative prompts, or user requests to cloud providers. This guard makes cloud use explicit, reversible, and easy to audit.

## Behavior after upgrade

- Local memory, local chat, file learning, local artifacts, local media tools, and browser UI remain available without cloud mode.
- Teacher-model requests are blocked unless `CLOUD_ALLOWED=true`.
- Normal web UI chat only routes to linked cloud models when `CLOUD_ALLOWED=true`.
- "Ask all AI" requests return a clear local-first block message when cloud mode is disabled.
- OpenAI image generation and OpenRouter/Veo video generation require both user consent and `CLOUD_ALLOWED=true`.
- Blocked requests do not call provider APIs or expose API keys.

## Files changed

- `human_ai/services.py`
- `human_ai/agent.py`
- `human_ai/web_ui.py`
- `tests/test_services.py`
- `tests/test_gima.py`
- `tests/test_web_ui.py`
- `docs/UPGRADE_REPORT_2026-07-08_CLOUD_SAFETY.md`

## Verification plan

- Run targeted service tests for teacher, image, and video cloud gating.
- Run targeted agent tests for teacher-learning cloud gating.
- Run targeted web UI tests for all-AI and cloud-chat routing.
- Run Python syntax checks on changed modules and tests.

## Verification results

- `python3 -m py_compile human_ai/services.py human_ai/agent.py human_ai/web_ui.py tests/test_services.py tests/test_gima.py tests/test_web_ui.py` passed.
- Targeted service cloud-gate tests passed: 7 tests.
- Targeted Gima agent cloud-gate tests passed: 3 tests.
- Targeted web UI cloud-routing tests passed: 4 tests.
- Broader regression run passed: `python3 -m unittest -q tests.test_services tests.test_gima tests.test_web_ui` ran 126 tests, with 1 skipped.
- Live `/api/status` check after the change showed Gima running, brain ready, and the local model available.

## Risk level

Low. The change is a safety gate around external API calls. It may surprise users who have saved API keys but did not set `CLOUD_ALLOWED=true`; however, the error message explains the required action and keeps Gima local-first by default.

## Rollback plan

Remove the `cloud_allowed` / `require_cloud_allowed` checks and revert the related tests if the project later replaces this environment flag with a richer UI-level consent system.
