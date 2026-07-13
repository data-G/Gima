# Gima OpenRouter Setup

This guide connects Gima to OpenRouter as a routed cloud brain while preserving Gima's local-first safety rules.

## Safety Rules

- Use a normal OpenRouter API key for model inference.
- Do not use an OpenRouter management key for chat, image, speech, or video requests.
- Do not commit real API keys to GitHub.
- Do not paste keys into source files, browser local storage, screenshots, reports, or public chats.
- Keep `CLOUD_ALLOWED=false` unless you intentionally want Gima to call cloud APIs.
- High-privacy work, API keys, passwords, secrets, and private documents must route to the local model.

## Environment Template

Copy `.env.example` only as a reference. Put real secrets in your local secret store, shell environment, or Gima API Bindings.

```bash
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=openrouter/auto
OPENROUTER_MAX_RETRIES=3
OPENROUTER_TIMEOUT_MS=120000
CLOUD_ALLOWED=false
DAILY_AI_BUDGET_USD=2
MONTHLY_AI_BUDGET_USD=30
```

For Gima's local app, the recommended path is:

1. Open Gima.
2. Go to `MCP / AI APIs`.
3. Save the correct key under the matching provider slot:
   - `OpenRouter Default` for general chat and reasoning.
   - `OpenRouter MAI Speech` for speech/audio providers.
   - `OpenRouter Veo Video` for video providers.
   - `OpenRouter Image` for image providers.
   - `OpenRouter Management Key` only for administrative key management.
4. Keep cloud mode off until you are ready to spend credits.

## Routing Modes

Gima exposes a planning endpoint:

```text
GET /api/ai-router/plan?message=debug%20this%20python%20class&mode=AUTO
```

Supported modes:

- `AUTO`: choose local or OpenRouter based on privacy, cloud permission, and task type.
- `LOCAL_ONLY`: force local model.
- `CLOUD_ONLY`: force OpenRouter unless blocked by safety policy.
- `FAST`: prefer fast and low-cost models.
- `BALANCED`: prefer general models.
- `BEST_QUALITY`: prefer stronger reasoning/coding/vision models.
- `LOWEST_COST`: prefer cheaper routes.
- `MANUAL`: use the supplied `model` parameter.

Task categories include chat, coding, debugging, research, data analysis, long documents, vision, creative writing, translation, summarization, agent planning, tool use, and private local tasks.

## Privacy Behavior

The router keeps these requests local:

- `privacy=high`
- Prompts containing secrets, API keys, passwords, or private document hints.
- Manual `LOCAL_ONLY` mode.

The `/api/ai-router/plan` response intentionally returns no API key, authorization header, or hidden secret value.

Example safe response fields:

```json
{
  "provider": "local",
  "task_category": "PRIVATE_LOCAL_TASK",
  "security": {
    "secrets_returned": false,
    "management_key_used_for_inference": false
  }
}
```

## Model Selection

Gima can use OpenRouter's `openrouter/auto` as the default. You can also configure task-specific models in the OpenRouter routing panel:

- Coding/debugging model.
- Vision model.
- Long-context model.
- Creative model.
- Fallback models.

Fallbacks should usually include:

```text
openrouter/auto
openrouter/free
```

## Budget And Usage Tracking

Gima records estimated usage in:

```text
.human-ai/usage/ai_usage_logs.csv
```

The log stores request IDs, provider, model, token counts, estimated cost, latency, success state, and fallback status. It must not store API keys or raw private prompts.

Recommended budget settings:

```bash
DAILY_AI_BUDGET_USD=2
MONTHLY_AI_BUDGET_USD=30
```

Provider-side limits still apply. Gima's local budget settings are a safety layer, not a billing guarantee.

## Production Deployment

For Cloud Run or another hosted deployment:

- Store keys in Secret Manager or the platform's managed secret system.
- Mount secrets as environment variables at runtime.
- Keep `.env` files out of containers and Git.
- Set `CLOUD_ALLOWED=true` only for deployments that are permitted to call cloud models.
- Use separate keys for chat, image, video, speech, and admin operations.
- Rotate keys after accidental exposure.

## Testing Without Spending Credits

Tests should mock OpenRouter HTTP calls. They should verify:

- Correct endpoint and headers.
- No management key is used for inference.
- Private prompts route local.
- Fallback model list is preserved.
- Usage logs do not contain secrets.
- UI planning endpoints return model plans without secret material.

Useful local commands:

```bash
python3 -m py_compile human_ai/openrouter_router.py human_ai/web_ui.py human_ai/services.py human_ai/secrets.py
python3 -m unittest tests.test_services tests.test_web_ui
```

## Troubleshooting

If Gima returns `HTTP 500` for internet or model calls:

- Check `/api/status`.
- Confirm the right OpenRouter key is linked.
- Confirm `CLOUD_ALLOWED=true` only when cloud calls are intended.
- Test `/api/ai-router/plan` before sending a real cloud request.
- Check `.human-ai/brain.log` and `.human-ai/usage/ai_usage_logs.csv`.
- Verify the selected OpenRouter model still exists and supports the requested capability.

If a management key was pasted into the wrong place, remove it from model inference settings, rotate the key, and save a normal OpenRouter API key for inference.
