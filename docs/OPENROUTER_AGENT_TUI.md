# Gima OpenRouter Agent TUI

## What Was Added

Gima now includes a separate OpenRouter-powered terminal agent scaffold at:

`apps/gima-openrouter-agent`

It follows the OpenRouter `create-agent-tui` skill architecture:

- `@openrouter/agent` handles model calls, tools, loop execution, stop conditions, streaming, and cost limits.
- The TUI provides local configuration, CLI commands, session logs, tool rendering, and Gima-specific tools.
- The request path uses OpenRouter app attribution, provider routing preferences, fallback models, cost limits, and `store: false`.

## Safety Defaults

The generated agent is read-only by default for local machine tools:

- `file_read`
- `list_dir`
- `glob`
- `grep`
- `gima_status`

It also enables OpenRouter server-side:

- `openrouter:web_search`
- `openrouter:datetime`

Write/edit/shell tools are intentionally not enabled yet. Add them only with an approval gate.

Provider privacy defaults:

- `dataCollection: "deny"`
- `store: false`
- `allowFallbacks: true`
- `sort: "latency"`

## Run It

```bash
cd apps/gima-openrouter-agent
export OPENROUTER_API_KEY="your OpenRouter key"
pnpm install
pnpm start
```

Bundled Codex runtime path if system `pnpm` is missing:

```bash
/Users/gimhangunarathne/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm install
/Users/gimhangunarathne/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/pnpm start
```

Useful environment settings:

```bash
export AGENT_MODEL="~openai/gpt-latest"
export AGENT_FALLBACK_MODELS="openai/gpt-4o-mini,google/gemini-2.5-flash"
export AGENT_DATA_COLLECTION="deny"
export AGENT_PROVIDER_SORT="latency"
```

## Commands

- `/help`
- `/model <openrouter-model-id>`
- `/new`
- `/session`
- `/exit`

## Next Upgrade

Add approval-gated file edit and shell tools, then expose this agent from the Gima web UI as a controlled "OpenRouter Agent" mode.
