import { OpenRouter } from "@openrouter/agent";
import type { Item } from "@openrouter/agent";
import { maxCost, stepCountIs } from "@openrouter/agent/stop-conditions";
import type { AgentConfig } from "./config.js";
import { tools } from "./tools/index.js";

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string };

export type AgentEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; name: string; callId: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; callId: string; output: string }
  | { type: "reasoning"; delta: string };

export async function runAgent(
  config: AgentConfig,
  input: string | ChatMessage[],
  options?: { onEvent?: (event: AgentEvent) => void; signal?: AbortSignal },
) {
  const client = new OpenRouter({
    apiKey: config.apiKey,
    httpReferer: config.httpReferer,
    appTitle: config.appTitle,
  });
  const models = [config.model, ...config.fallbackModels].filter(Boolean);
  const result = client.callModel({
    ...(models.length > 1 ? { models } : { model: config.model }),
    instructions: config.systemPrompt.replace("{cwd}", process.cwd()),
    input: input as string | Item[],
    tools,
    provider: {
      allowFallbacks: config.provider.allowFallbacks,
      dataCollection: config.provider.dataCollection,
      sort: config.provider.sort,
      zdr: config.provider.zdr,
    },
    store: false,
    metadata: {
      app: "gima-openrouter-agent",
      mode: "read-only-tui",
    },
    stopWhen: [stepCountIs(config.maxSteps), maxCost(config.maxCost)],
    allowFinalResponse: "Summarize the completed work and any limits clearly.",
  });

  if (options?.onEvent) {
    const textByItem = new Map<string, number>();
    const callNames = new Map<string, string>();
    for await (const item of result.getItemsStream()) {
      if (options.signal?.aborted) break;
      if (item.type === "message") {
        const text =
          item.content
            ?.filter((content): content is { type: "output_text"; text: string } => "text" in content)
            .map((content) => content.text)
            .join("") ?? "";
        const prev = textByItem.get(item.id) ?? 0;
        if (text.length > prev) {
          options.onEvent({ type: "text", delta: text.slice(prev) });
          textByItem.set(item.id, text.length);
        }
      } else if (item.type === "function_call") {
        callNames.set(item.callId, item.name);
        if (item.status === "completed") {
          let args: Record<string, unknown> = {};
          try {
            args = item.arguments ? (JSON.parse(item.arguments) as Record<string, unknown>) : {};
          } catch {
            args = {};
          }
          options.onEvent({ type: "tool_call", name: item.name, callId: item.callId, args });
        }
      } else if (item.type === "function_call_output") {
        const output = typeof item.output === "string" ? item.output : JSON.stringify(item.output);
        options.onEvent({
          type: "tool_result",
          name: callNames.get(item.callId) ?? "unknown",
          callId: item.callId,
          output: output.length > 240 ? output.slice(0, 240) + "..." : output,
        });
      } else if (item.type === "reasoning") {
        const text = item.summary?.map((part: { text: string }) => part.text).join("") ?? "";
        if (text) options.onEvent({ type: "reasoning", delta: text });
      }
    }
  }

  const response = await result.getResponse();
  return { text: response.outputText ?? "", usage: response.usage, output: response.output };
}

export async function runAgentWithRetry(
  config: AgentConfig,
  input: string | ChatMessage[],
  options?: { onEvent?: (event: AgentEvent) => void; signal?: AbortSignal; maxRetries?: number },
) {
  for (let attempt = 0, max = options?.maxRetries ?? 2; attempt <= max; attempt++) {
    try {
      return await runAgent(config, input, options);
    } catch (error) {
      const status = typeof error === "object" && error !== null && "status" in error ? Number(error.status) : 0;
      if (!(status === 429 || (status >= 500 && status < 600)) || attempt === max) throw error;
      await new Promise((resolve) => setTimeout(resolve, Math.min(1000 * 2 ** attempt, 15000)));
    }
  }
  throw new Error("unreachable");
}
