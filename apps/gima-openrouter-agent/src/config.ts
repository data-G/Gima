import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

export type ToolDisplay = "grouped" | "emoji" | "minimal" | "hidden";
export type InputStyle = "bordered" | "plain";

export interface DisplayConfig {
  toolDisplay: ToolDisplay;
  inputStyle: InputStyle;
  reasoning: boolean;
}

export interface AgentConfig {
  apiKey: string;
  httpReferer?: string;
  appTitle?: string;
  model: string;
  fallbackModels: string[];
  systemPrompt: string;
  maxSteps: number;
  maxCost: number;
  sessionDir: string;
  provider: {
    allowFallbacks: boolean;
    dataCollection: "allow" | "deny";
    sort: string;
    zdr: boolean;
  };
  display: DisplayConfig;
}

const DEFAULTS: AgentConfig = {
  apiKey: "",
  httpReferer: "http://127.0.0.1:8787/",
  appTitle: "Gima OpenRouter Agent",
  model: "openai/gpt-4o-mini",
  fallbackModels: [],
  systemPrompt: [
    "You are Gima Agent, a careful OpenRouter-powered terminal assistant for the Gima workspace.",
    "",
    "Current working directory: {cwd}",
    "",
    "Operating rules:",
    "- Use tools to verify local facts before answering.",
    "- Keep local file access read-only unless the human explicitly upgrades this TUI with approval-gated write tools.",
    "- Do not ask for or reveal API keys, tokens, cookies, credentials, or private secrets.",
    "- Use web search only for public information and cite what you used in plain language.",
    "- For security or reverse-engineering tasks, ask whether the user owns the system or has written permission, then ask for scope.",
    "- Be concise, practical, and honest about uncertainty.",
  ].join("\n"),
  maxSteps: 8,
  maxCost: 0.25,
  sessionDir: ".sessions",
  provider: {
    allowFallbacks: true,
    dataCollection: "deny",
    sort: "latency",
    zdr: false,
  },
  display: {
    toolDisplay: "grouped",
    inputStyle: "bordered",
    reasoning: false,
  },
};

function loadDotEnv(): void {
  const envPath = resolve(".env");
  if (!existsSync(envPath)) return;
  const lines = readFileSync(envPath, "utf-8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
    if (!process.env[key]) process.env[key] = value;
  }
}

export function loadConfig(overrides: Partial<AgentConfig> = {}): AgentConfig {
  loadDotEnv();
  let config: AgentConfig = { ...DEFAULTS, display: { ...DEFAULTS.display } };
  const configPath = resolve("agent.config.json");
  if (existsSync(configPath)) {
    const file = JSON.parse(readFileSync(configPath, "utf-8")) as Partial<AgentConfig>;
    config = {
      ...config,
      ...file,
      provider: { ...config.provider, ...(file.provider ?? {}) },
      display: { ...config.display, ...(file.display ?? {}) },
    };
  }
  if (process.env.OPENROUTER_API_KEY) config.apiKey = process.env.OPENROUTER_API_KEY;
  if (process.env.AGENT_HTTP_REFERER) config.httpReferer = process.env.AGENT_HTTP_REFERER;
  if (process.env.AGENT_APP_TITLE) config.appTitle = process.env.AGENT_APP_TITLE;
  if (process.env.AGENT_MODEL) config.model = process.env.AGENT_MODEL;
  if (process.env.AGENT_FALLBACK_MODELS) {
    config.fallbackModels = process.env.AGENT_FALLBACK_MODELS.split(",")
      .map((model) => model.trim())
      .filter(Boolean);
  }
  if (process.env.AGENT_MAX_STEPS) config.maxSteps = Number(process.env.AGENT_MAX_STEPS);
  if (process.env.AGENT_MAX_COST) config.maxCost = Number(process.env.AGENT_MAX_COST);
  if (process.env.AGENT_PROVIDER_SORT) config.provider.sort = process.env.AGENT_PROVIDER_SORT;
  if (process.env.AGENT_DATA_COLLECTION === "allow" || process.env.AGENT_DATA_COLLECTION === "deny") {
    config.provider.dataCollection = process.env.AGENT_DATA_COLLECTION;
  }
  if (process.env.AGENT_ZDR === "true") config.provider.zdr = true;
  config = {
    ...config,
    ...overrides,
    provider: { ...config.provider, ...(overrides.provider ?? {}) },
    display: { ...config.display, ...(overrides.display ?? {}) },
  };
  if (!config.apiKey) {
    throw new Error("OPENROUTER_API_KEY is required. Export it or create a local .env from .env.example.");
  }
  return config;
}
