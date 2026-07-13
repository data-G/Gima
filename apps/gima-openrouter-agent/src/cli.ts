import { createInterface } from "node:readline";
import { loadConfig, type AgentConfig } from "./config.js";
import { runAgentWithRetry, type AgentEvent } from "./agent.js";
import { listSessions, SessionLog } from "./session.js";

const RESET = "\x1b[0m";
const BOLD = "\x1b[1m";
const DIM = "\x1b[2m";
const CYAN = "\x1b[36m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const GRAY = "\x1b[90m";

function formatTokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function summarizeArgs(name: string, args: Record<string, unknown>): string {
  const key =
    {
      file_read: "path",
      list_dir: "path",
      glob: "pattern",
      grep: "pattern",
      gima_status: "url",
      web_search: "query",
    }[name] ?? Object.keys(args)[0];
  if (!key || !(key in args)) return "";
  const value = String(args[key]);
  return `${key}=${value.length > 56 ? value.slice(0, 56) + "..." : value}`;
}

function printBanner(config: AgentConfig): void {
  const width = Math.min(process.stdout.columns || 72, 72);
  const line = GRAY + "─".repeat(width) + RESET;
  console.log(`\n${line}`);
  console.log(` ${BOLD}Gima OpenRouter Agent${RESET} ${DIM}v0.1.0${RESET}`);
  console.log(` ${DIM}model${RESET} ${CYAN}${config.model}${RESET}`);
  console.log(` ${DIM}commands${RESET} /help /model /new /session /exit`);
  console.log(`${line}\n`);
}

function printHelp(): void {
  console.log([
    `${BOLD}Commands${RESET}`,
    "  /help                Show this help",
    "  /model <id>          Switch OpenRouter model for this session",
    "  /new                 Start a fresh session log",
    "  /session             Show session file and recent session logs",
    "  /exit                Quit",
    "",
    `${BOLD}Tools${RESET}`,
    "  OpenRouter server: web_search, datetime",
    "  Local read-only: file_read, list_dir, glob, grep, gima_status",
  ].join("\n"));
}

async function main(): Promise<void> {
  let config = loadConfig();
  let session = new SessionLog(config.sessionDir);
  printBanner(config);

  const rl = createInterface({ input: process.stdin, output: process.stdout, prompt: `${GREEN}>${RESET} ` });

  const getInput = () =>
    new Promise<string>((resolve) => {
      if (config.display.inputStyle === "bordered") {
        const width = Math.min(process.stdout.columns || 72, 72);
        console.log(GRAY + "─".repeat(width) + RESET);
      }
      rl.prompt();
      rl.once("line", resolve);
    });

  while (true) {
    const input = await getInput();
    const trimmed = input.trim();
    if (!trimmed) continue;

    if (trimmed === "/help") {
      printHelp();
      continue;
    }
    if (trimmed === "/exit" || trimmed === "exit" || trimmed === "quit") {
      rl.close();
      return;
    }
    if (trimmed === "/new") {
      session = new SessionLog(config.sessionDir);
      console.log(`${GREEN}New session:${RESET} ${session.path}`);
      continue;
    }
    if (trimmed.startsWith("/model")) {
      const model = trimmed.replace("/model", "").trim();
      if (!model) {
        console.log(`${CYAN}${config.model}${RESET}`);
      } else {
        config = { ...config, model };
        console.log(`${GREEN}Model set:${RESET} ${config.model}`);
      }
      continue;
    }
    if (trimmed === "/session") {
      const sessions = await listSessions(config.sessionDir);
      console.log(`${GREEN}Current:${RESET} ${session.path}`);
      console.log(sessions.slice(0, 5).map((entry) => `  ${entry}`).join("\n") || "  no saved sessions yet");
      continue;
    }

    await session.append({ role: "user", content: trimmed, model: config.model });
    console.log();
    let streaming = false;
    let started = false;
    const toolStart = new Map<string, number>();
    const spin = setInterval(() => {
      if (!started) process.stdout.write(`\r${DIM}Working...${RESET}`);
    }, 400);

    const handleEvent = (event: AgentEvent) => {
      if (!started) {
        started = true;
        process.stdout.write("\r\x1b[K");
      }
      if (event.type === "text") {
        streaming = true;
        process.stdout.write(event.delta);
      } else if (event.type === "tool_call" && config.display.toolDisplay !== "hidden") {
        if (streaming) {
          process.stdout.write("\n");
          streaming = false;
        }
        toolStart.set(event.callId, Date.now());
        if (config.display.toolDisplay === "minimal") {
          console.log(` ${DIM}${event.name}${RESET}`);
        } else {
          console.log(` ${YELLOW}⚡${RESET} ${DIM}${event.name} ${summarizeArgs(event.name, event.args)}${RESET}`);
        }
      } else if (event.type === "tool_result" && config.display.toolDisplay !== "hidden") {
        const ms = Date.now() - (toolStart.get(event.callId) ?? Date.now());
        console.log(` ${GREEN}✓${RESET} ${DIM}${event.name} (${(ms / 1000).toFixed(1)}s)${RESET}`);
        started = false;
      } else if (event.type === "reasoning" && config.display.reasoning) {
        console.log(`${GRAY}${event.delta}${RESET}`);
      }
    };

    try {
      const result = await runAgentWithRetry(config, trimmed, { onEvent: handleEvent });
      clearInterval(spin);
      if (streaming) process.stdout.write(RESET);
      const inputTokens = result.usage?.inputTokens ?? 0;
      const outputTokens = result.usage?.outputTokens ?? 0;
      console.log(`\n${GRAY} ${formatTokens(inputTokens)} in · ${formatTokens(outputTokens)} out${RESET}\n`);
      await session.append({ role: "assistant", content: result.text, model: config.model, usage: result.usage });
    } catch (error) {
      clearInterval(spin);
      if (streaming) process.stdout.write(RESET);
      const message = error instanceof Error ? error.message : String(error);
      console.log(`\n${YELLOW}Error:${RESET} ${message}\n`);
      await session.append({ role: "system", content: `error: ${message}`, model: config.model });
    }
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
