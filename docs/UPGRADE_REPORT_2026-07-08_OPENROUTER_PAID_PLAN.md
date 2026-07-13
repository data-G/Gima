# Gima Upgrade Report - 2026-07-08

## Improvement chosen

Paid OpenRouter model planner for Gima's hybrid local-first architecture.

## Summary

Gima now turns the pasted paid OpenRouter comparison into a live planning endpoint and dashboard card. The planner uses the OpenRouter model catalog when available, ranks paid models by use case, and writes reusable CSV, Markdown, and JSON artifacts into `hands/out/openrouter_paid_planner`.

The recommended strategy is:

1. Local first for unlimited/private daily work.
2. Cheap OpenRouter models for normal cloud help.
3. Premium OpenRouter models only for hard reasoning, coding, long documents, vision, or media.
4. Explicit consent and budget controls for image/video/speech generation.

## Files changed

- `human_ai/openrouter_paid_planner.py`
- `human_ai/web_ui.py`
- `tests/test_openrouter_paid_planner.py`
- `tests/test_web_ui.py`
- `docs/UPGRADE_REPORT_2026-07-08_OPENROUTER_PAID_PLAN.md`

## Verification results

- Python compile passed for changed modules and tests.
- Focused paid planner and dashboard tests passed.
- Broader regression run passed: 79 tests, with 1 skipped.

## Safety defaults

- The planner does not call paid completions.
- Catalog refresh uses OpenRouter's public model list only.
- The planner recommends local-first routing and key budget caps.
- Private files should not be sent to cloud unless `CLOUD_ALLOWED=true` and the user approves.

## Next recommended upgrade

Connect paid-model recommendations to live usage logs so Gima can compare model cost, latency, and answer quality after each approved cloud call.
