import { serverTool } from "@openrouter/agent";
import { fileReadTool } from "./file-read.js";
import { gimaStatusTool } from "./gima-status.js";
import { globTool } from "./glob.js";
import { grepTool } from "./grep.js";
import { listDirTool } from "./list-dir.js";

export const tools = [
  fileReadTool,
  globTool,
  grepTool,
  listDirTool,
  gimaStatusTool,
  serverTool({ type: "openrouter:web_search" }),
  serverTool({ type: "openrouter:datetime", parameters: { timezone: "Asia/Tokyo" } }),
];
