# Gima Free LLM API Planner

## Purpose

The Free LLM API Planner helps Gima choose practical free or trial LLM providers for a task before sending any cloud request. It is a local planning feature: it does not call provider APIs, spend credits, or expose API keys.

## Source

Initial provider data comes from the OpenRouter article pasted by the user: "Free LLM APIs Compared: Rate Limits, Models, and Real Costs" dated 2026-06-15.

Because free tiers, rate limits, models, and privacy terms change often, Gima should treat this as planning guidance and recheck current provider documentation before production use.

## Providers Included

- OpenRouter
- Google AI Studio
- Groq
- Mistral Experiment
- Cerebras
- GitHub Models
- Cloudflare Workers AI
- Cohere Trial
- Hugging Face
- NVIDIA NIM
- Chutes
- SambaNova Trial
- Vercel AI Gateway
- DeepSeek Trial

## What It Optimizes

- Task fit: speed, voice, coding, long context, batch work, edge/serverless, reasoning, and open-source exploration.
- Privacy posture: balanced, strict/private, or open/public.
- Integration fit: OpenAI-compatible endpoints are easier for Gima to route through.
- Sustainability: trial credits are ranked lower than permanent free tiers for ongoing work.

## Safety Rules

- Use local inference for private files, customer data, secrets, and proprietary code unless `CLOUD_ALLOWED=true` and the user approves.
- Prefer no-training providers for sensitive work.
- Use routers for variety and failover; use direct providers when native features or full native quota matter.
- Treat trial credits as evaluation budget, not production capacity.

## Web UI

Open Gima and use:

`MCP / AI APIs` -> `Free LLM planner task` -> `Plan Free LLM Route`

Example tasks:

- `fast voice realtime chat`
- `long private company document analysis`
- `batch summarize many public articles`
- `coding refactor repo`

## API

```text
GET /api/free-llm-plan?task=fast%20voice%20chat&privacy=balanced&limit=6
```

Privacy options:

- `balanced`
- `strict`
- `open`

## Next Upgrade

Add real provider adapters for Groq, Cerebras, GitHub Models, and Cloudflare Workers AI behind `CLOUD_ALLOWED=true`, with provider health checks, quota tracking, and automatic failover.
