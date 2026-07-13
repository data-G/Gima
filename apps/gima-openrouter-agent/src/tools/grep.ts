import { readFile } from "node:fs/promises";
import { glob } from "glob";
import { tool } from "@openrouter/agent/tool";
import { z } from "zod";

export const grepTool = tool({
  name: "grep",
  description: "Search file contents with a JavaScript regular expression.",
  inputSchema: z.object({
    pattern: z.string(),
    include: z.string().default("**/*"),
    cwd: z.string().default("."),
    limit: z.number().int().positive().max(500).default(100),
  }),
  execute: async ({ pattern, include, cwd, limit }) => {
    try {
      const regex = new RegExp(pattern, "i");
      const files = await glob(include, {
        cwd,
        dot: true,
        nodir: true,
        ignore: ["**/node_modules/**", "**/.git/**", "**/.human-ai/**", "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.pdf"],
      });
      const results: Array<{ file: string; line: number; text: string }> = [];
      for (const file of files) {
        if (results.length >= limit) break;
        let text = "";
        try {
          text = await readFile(`${cwd}/${file}`, "utf-8");
        } catch {
          continue;
        }
        const lines = text.split("\n");
        for (let i = 0; i < lines.length && results.length < limit; i++) {
          if (regex.test(lines[i])) results.push({ file, line: i + 1, text: lines[i].slice(0, 400) });
        }
      }
      return { pattern, include, results, truncated: results.length >= limit };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error) };
    }
  },
});
