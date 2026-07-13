import { glob } from "glob";
import { tool } from "@openrouter/agent/tool";
import { z } from "zod";

export const globTool = tool({
  name: "glob",
  description: "Find files by glob pattern.",
  inputSchema: z.object({
    pattern: z.string(),
    cwd: z.string().default("."),
    limit: z.number().int().positive().max(1000).default(200),
  }),
  execute: async ({ pattern, cwd, limit }) => {
    try {
      const matches = await glob(pattern, {
        cwd,
        dot: true,
        nodir: true,
        ignore: ["**/node_modules/**", "**/.git/**", "**/.human-ai/**"],
      });
      return { cwd, pattern, matches: matches.slice(0, limit), truncated: matches.length > limit };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error) };
    }
  },
});
