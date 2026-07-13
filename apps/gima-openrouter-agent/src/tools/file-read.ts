import { readFile } from "node:fs/promises";
import { tool } from "@openrouter/agent/tool";
import { z } from "zod";

const DEFAULT_LINE_LIMIT = 300;
const MAX_LINE_CHARS = 1600;

export const fileReadTool = tool({
  name: "file_read",
  description: "Read a UTF-8 text file by absolute or workspace-relative path. Output is capped and paginated.",
  inputSchema: z.object({
    path: z.string(),
    offset: z.number().int().positive().optional(),
    limit: z.number().int().positive().max(1000).optional(),
  }),
  execute: async ({ path, offset, limit }) => {
    try {
      const content = await readFile(path, "utf-8");
      const lines = content.split("\n");
      const start = offset ? offset - 1 : 0;
      const end = Math.min(start + (limit ?? DEFAULT_LINE_LIMIT), lines.length);
      let longLines = 0;
      const slice = lines.slice(start, end).map((line) => {
        if (line.length <= MAX_LINE_CHARS) return line;
        longLines++;
        return line.slice(0, MAX_LINE_CHARS) + `... [line truncated, ${line.length - MAX_LINE_CHARS} chars dropped]`;
      });
      return {
        content: slice.join("\n"),
        totalLines: lines.length,
        shown: `${start + 1}-${end}`,
        truncated: end < lines.length || longLines > 0,
        nextOffset: end < lines.length ? end + 1 : undefined,
      };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error) };
    }
  },
});
