# Gima Upgrade Report - 2026-07-08

## Improvement chosen

OpenRouter Agent TUI for Gima, aligned with the OpenRouter `create-agent-tui` skill and current Agent SDK documentation.

## Summary

Gima now has a separate TypeScript terminal agent in `apps/gima-openrouter-agent`. It uses `@openrouter/agent` for the model loop, tool execution, streaming, stop conditions, and cost limits.

The agent is intentionally read-only for local machine tools. It can inspect files, search the repo, check Gima status, and use OpenRouter server-side web search/datetime, but it cannot write files or run shell commands through the model loop.

## Why it matters

This gives Gima a modern agent harness without risking the existing Python web app. It also creates a clean place to test OpenRouter models, fallback routing, server tools, and session persistence.

## Files changed

- `apps/gima-openrouter-agent/`
- `apps/README.md`
- `docs/OPENROUTER_AGENT_TUI.md`
- `docs/UPGRADE_REPORT_2026-07-08_OPENROUTER_AGENT_TUI.md`

## Verification results

- `pnpm install --ignore-scripts` passed.
- `./node_modules/.bin/tsc --noEmit` passed.
- Missing-key startup test returned the expected safe error.
- Fake-key `/help` and `/exit` smoke test passed without sending a model request.

## Safety defaults

- Local tools are read-only.
- API keys are loaded from environment or local `.env`, never committed.
- Provider routing defaults to `dataCollection: "deny"`.
- Requests set `store: false`.
- Write/edit/shell tools are deferred until approval gates exist.

## Next recommended upgrade

Add approval-gated file edit and shell tools using OpenRouter Agent SDK tool approval/state persistence, then expose the TUI as a controlled mode in the Gima web UI.
