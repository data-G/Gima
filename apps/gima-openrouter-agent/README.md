# Gima OpenRouter Agent TUI

This is a safe terminal agent built from the OpenRouter `create-agent-tui` skill pattern.

It uses `@openrouter/agent` for the model/tool loop and gives Gima a separate terminal interface with:

- OpenRouter model calls
- OpenRouter server tools: web search and datetime
- Read-only local tools: file read, directory list, glob, grep
- A custom `gima_status` tool
- JSONL session persistence
- OpenRouter app attribution headers
- Provider routing preferences with `dataCollection: "deny"` by default
- Slash commands: `/help`, `/model`, `/new`, `/session`, `/exit`

## Start

```bash
cd apps/gima-openrouter-agent
cp .env.example .env
```

Add your real key to `.env` or export it in the terminal. Do not commit secrets.

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
pnpm install
pnpm start
```

This app does not edit Gima's `.env` and does not store API keys in the repo.

## Safer Default

The first version is intentionally read-only for local tools. It can inspect files, search the repo, and check Gima status, but it cannot write files or run shell commands through the model loop.

Add write/edit/shell tools only after adding explicit approval gates.

## OpenRouter Routing

The TUI follows the current OpenRouter Agent SDK `OpenRouter.callModel()` pattern. It supports:

- `AGENT_MODEL`, including latest aliases such as `~openai/gpt-latest`
- `AGENT_FALLBACK_MODELS`, comma-separated
- `AGENT_PROVIDER_SORT`, for example `latency`, `throughput`, or `price`
- `AGENT_DATA_COLLECTION=deny` by default
- `AGENT_ZDR=true` when you want to request zero-data-retention endpoints only
- `AGENT_HTTP_REFERER` and `AGENT_APP_TITLE` for OpenRouter app attribution
