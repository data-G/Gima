import { readdir, stat } from "node:fs/promises";
import { join } from "node:path";
import { tool } from "@openrouter/agent/tool";
import { z } from "zod";

export const listDirTool = tool({
  name: "list_dir",
  description: "List files and folders in a directory.",
  inputSchema: z.object({
    path: z.string().default("."),
    limit: z.number().int().positive().max(500).default(100),
  }),
  execute: async ({ path, limit }) => {
    try {
      const entries = await readdir(path);
      const rows = await Promise.all(
        entries.slice(0, limit).map(async (entry) => {
          const full = join(path, entry);
          const s = await stat(full);
          return { name: entry, type: s.isDirectory() ? "directory" : "file", size: s.size };
        }),
      );
      return { path, entries: rows, truncated: entries.length > limit };
    } catch (error) {
      return { error: error instanceof Error ? error.message : String(error) };
    }
  },
});
