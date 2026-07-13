import { readFile } from "node:fs/promises";
import { tool } from "@openrouter/agent/tool";
import { z } from "zod";

export const gimaStatusTool = tool({
  name: "gima_status",
  description: "Check the local Gima web server status endpoint.",
  inputSchema: z.object({
    url: z.string().default("http://127.0.0.1:8787/api/status"),
  }),
  execute: async ({ url }) => {
    try {
      const response = await fetch(url);
      return { ok: response.ok, status: response.status, data: await response.json() };
    } catch (error) {
      const pidPath = "../../.human-ai/runtime/web_ui.pid";
      let pid = "";
      try {
        pid = await readFile(pidPath, "utf-8");
      } catch {
        // ignore
      }
      return { ok: false, error: error instanceof Error ? error.message : String(error), pid: pid.trim() || undefined };
    }
  },
});
