# Gima Upgrade Report - 2026-07-08

## Improvement chosen

Free LLM API Planner from the OpenRouter free-API comparison pasted by the user.

## Summary

Gima now has a local planner that recommends free or trial LLM providers by task, privacy posture, rate-limit shape, integration style, and sustainability. The planner is exposed through both the web UI and `/api/free-llm-plan`.

This does not call external APIs. It is a safe routing decision layer that helps Gima decide when OpenRouter, Groq, Cerebras, Google AI Studio, GitHub Models, Mistral, Cloudflare Workers AI, Cohere, Hugging Face, NVIDIA NIM, Chutes, SambaNova, Vercel AI Gateway, or DeepSeek trial credits make sense.

## Why it matters

Gima should not blindly use a saved API key. A modern personal AI workspace needs model routing intelligence: fast models for voice, long-context models for documents, no-training providers for private work, and routers for failover.

This upgrade moves Gima closer to a practical local-first agent that can use cloud APIs only when appropriate, explicit, and reviewable.

## Behavior after upgrade

- Gima can rank free LLM providers for a user task.
- Strict privacy mode penalizes providers whose free tier may train on prompts or responses.
- Groq is favored for low-latency voice/chat tasks.
- OpenRouter is favored as the default multi-model router and failover path.
- Trial-credit providers are treated as evaluation options, not production capacity.
- The planner returns safety rules with every response.

## Files changed

- `human_ai/free_llm_planner.py`
- `human_ai/web_ui.py`
- `tests/test_free_llm_planner.py`
- `tests/test_web_ui.py`
- `docs/FREE_LLM_API_PLANNER.md`
- `docs/UPGRADE_REPORT_2026-07-08_FREE_LLM_PLANNER.md`

## Verification results

- `python3 -m py_compile human_ai/free_llm_planner.py human_ai/web_ui.py tests/test_free_llm_planner.py tests/test_web_ui.py` passed.
- Focused planner and dashboard tests passed: `python3 -m unittest tests.test_free_llm_planner tests.test_web_ui.WebUiTests.test_web_api_dashboards_report_capabilities_deployments_agents_and_outputs`.
- Broader regression run passed: `python3 -m unittest tests.test_free_llm_planner tests.test_public_apis tests.test_services tests.test_web_ui` ran 72 tests, with 1 skipped.

## Risk level

Low. The feature is local-only planning data and UI/API rendering. It does not transmit prompts to providers, edit secrets, or change live cloud routing behavior.

## Known limits

- Provider rate limits and free-tier policies may change.
- Recommendations are heuristic, not a benchmark result.
- Real routing adapters still need provider-specific health checks and quota accounting.

## Next recommended upgrade

Add provider adapters for Groq, Cerebras, GitHub Models, and Cloudflare Workers AI behind `CLOUD_ALLOWED=true`, then connect the planner to live health, quota, and latency data.
