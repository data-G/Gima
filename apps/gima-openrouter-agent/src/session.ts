import { mkdir, appendFile, readdir, stat } from "node:fs/promises";
import { join } from "node:path";

export interface SessionRecord {
  time: string;
  role: "user" | "assistant" | "system";
  content: string;
  model?: string;
  usage?: unknown;
}

export class SessionLog {
  readonly path: string;

  constructor(private readonly dir: string) {
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    this.path = join(dir, `${stamp}.jsonl`);
  }

  async append(record: Omit<SessionRecord, "time">): Promise<void> {
    await mkdir(this.dir, { recursive: true });
    const line = JSON.stringify({ time: new Date().toISOString(), ...record }) + "\n";
    await appendFile(this.path, line, "utf-8");
  }
}

export async function listSessions(dir: string): Promise<string[]> {
  try {
    const entries = await readdir(dir);
    const rows = await Promise.all(
      entries
        .filter((entry) => entry.endsWith(".jsonl"))
        .map(async (entry) => {
          const path = join(dir, entry);
          const s = await stat(path);
          return { entry, mtime: s.mtimeMs };
        }),
    );
    return rows.sort((a, b) => b.mtime - a.mtime).map((row) => row.entry);
  } catch {
    return [];
  }
}
