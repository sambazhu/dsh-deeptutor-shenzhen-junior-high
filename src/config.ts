/**
 * DeepTutor bridge: shared configuration (env vars) and small helpers.
 *
 * Config (optional env vars, agent-agnostic):
 *   DEEPTUTOR_SSH_HOST       SSH host alias (remote deployment; unset/empty = local deployment)
 *   DEEPTUTOR_API_BASE       API base URL (default http://127.0.0.1:8001, local or tunnel port)
 *   DEEPTUTOR_LOCAL_BIN      local deeptutor executable (local CLI fallback; default: deeptutor on PATH)
 *   DEEPTUTOR_HOME           local DEEPTUTOR_HOME workspace (default: ~/.deeptutor)
 *   DEEPTUTOR_REMOTE_BIN     remote deeptutor binary path (remote CLI fallback)
 *   DEEPTUTOR_REMOTE_HOME    remote DEEPTUTOR_HOME workspace (remote)
 *   DEEPTUTOR_LEDGER_ROOT    learning ledger root directory (Shenzhen Grade 7 customization)
 *   DEEPTUTOR_SUBJECT_KB_MAP JSON map of subject -> KB name (default: {"数学":"sz-g7-math-bsd"})
 *   DEEPTUTOR_WRONGBOOK_KB   wrong-question KB name (default: qiuyu-wrongbook)
 *   DEEPTUTOR_CHILD_MODE     when "1" or "true", prepend Socratic anti-ghostwriting guard
 */
import { homedir } from "node:os";
import { join } from "node:path";

export const SSH_HOST = process.env.DEEPTUTOR_SSH_HOST ?? "";
export const API_BASE = process.env.DEEPTUTOR_API_BASE ?? "http://127.0.0.1:8001";
export const TUNNEL_PORT = Number(new URL(API_BASE).port || 8001);
export const LOCAL_BIN = process.env.DEEPTUTOR_LOCAL_BIN ?? "deeptutor";
export const LOCAL_HOME =
  process.env.DEEPTUTOR_HOME ?? join(homedir(), ".deeptutor");
export const DEEPTUTOR_BIN =
  process.env.DEEPTUTOR_REMOTE_BIN ?? "/home/ubuntu/my-deeptutor/.venv/bin/deeptutor";
export const DEEPTUTOR_HOME = process.env.DEEPTUTOR_REMOTE_HOME ?? "/home/ubuntu/my-deeptutor";

export const LEDGER_ROOT =
  process.env.DEEPTUTOR_LEDGER_ROOT ??
  join(homedir(), "dshworkplace", "朱秋宇初一学习台账");

export const WRONGBOOK_KB =
  process.env.DEEPTUTOR_WRONGBOOK_KB ?? "qiuyu-wrongbook";

export const DEFAULT_SUBJECT_KB_MAP: Record<string, string> = {
  语文: "sz-g7-chinese-tb",
  chinese: "sz-g7-chinese-tb",
  数学: "sz-g7-math-bsd",
  math: "sz-g7-math-bsd",
  英语: "sz-g7-english-hj",
  english: "sz-g7-english-hj",
  地理: "sz-g7-geography-xj",
  geography: "sz-g7-geography-xj",
  历史: "sz-g7-history-tb",
  history: "sz-g7-history-tb",
  生物: "sz-g7-biology-rj",
  生物学: "sz-g7-biology-rj",
  biology: "sz-g7-biology-rj",
  道法: "sz-g7-morality-tb",
  道德与法治: "sz-g7-morality-tb",
  morality: "sz-g7-morality-tb",
};

export function getSubjectKbMap(
  rawJson = process.env.DEEPTUTOR_SUBJECT_KB_MAP,
): Record<string, string> {
  const merged: Record<string, string> = { ...DEFAULT_SUBJECT_KB_MAP };
  if (rawJson && rawJson.trim()) {
    try {
      const parsed = JSON.parse(rawJson);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        for (const [k, v] of Object.entries(parsed)) {
          if (typeof v === "string" && v.trim()) merged[k.trim()] = v.trim();
        }
      }
    } catch {
      /* ignore malformed JSON override */
    }
  }
  return merged;
}

export function resolveSubjectKbs(
  subject?: string,
  includeWrongbook = true,
  rawJson = process.env.DEEPTUTOR_SUBJECT_KB_MAP,
): string[] {
  const kbs: string[] = [];
  if (subject && subject.trim()) {
    const map = getSubjectKbMap(rawJson);
    const key = subject.trim();
    const mapped = map[key] ?? map[key.toLowerCase()];
    if (mapped) kbs.push(mapped);
  }
  if (includeWrongbook && WRONGBOOK_KB && !kbs.includes(WRONGBOOK_KB)) {
    kbs.push(WRONGBOOK_KB);
  }
  return kbs;
}

export const CHILD_MODE =
  process.env.DEEPTUTOR_CHILD_MODE === "1" ||
  process.env.DEEPTUTOR_CHILD_MODE === "true";

export const CHILD_MODE_GUARD_PREFIX =
  "【深圳初一伴读安全约束】你正在辅导深圳初一（七年级）学生朱秋宇。若本问题属于当天未完成的学校作业或测验，请采用苏格拉底式引导：先询问或肯定学生的思路、给出关键知识点提示与第一步方向，严禁直接给出可供照抄的完整最终答案。讲解数学题时请对齐北师大版七年级教材章节，并用两种不同方法交叉验证结论。\n\n";

export function applyChildModePrompt(
  prompt: string,
  childMode: boolean = CHILD_MODE,
): string {
  if (!childMode) return prompt;
  if (prompt.includes("【深圳初一伴读安全约束】")) return prompt;
  return CHILD_MODE_GUARD_PREFIX + prompt;
}

// Whether the user explicitly configured anything (show a one-time hint when not)
const IS_CONFIGURED = Boolean(
  process.env.DEEPTUTOR_SSH_HOST ||
    process.env.DEEPTUTOR_API_BASE ||
    process.env.DEEPTUTOR_LOCAL_BIN ||
    process.env.DEEPTUTOR_HOME ||
    process.env.DEEPTUTOR_REMOTE_BIN ||
    process.env.DEEPTUTOR_REMOTE_HOME,
);
let configHintShown = false;

export function configHint(): string {
  if (IS_CONFIGURED || configHintShown) return "";
  configHintShown = true;
  return (
    "⚠️ No DEEPTUTOR_* env vars detected; running in local-deployment mode (local serve / local CLI).\n" +
    '   Local deployment: export DEEPTUTOR_API_BASE="http://127.0.0.1:8001" (serve port; optional DEEPTUTOR_LOCAL_BIN)\n' +
    '   Remote deployment: export DEEPTUTOR_SSH_HOST="your-ssh-alias" plus DEEPTUTOR_API_BASE\n' +
    "   (See the SKILL's Configuration section; changing server/port only requires env vars)\n"
  );
}

export function configGuide(): string {
  return (
    "\n--- Configuration troubleshooting ---\n" +
    "Local deployment (deeptutor runs on this machine):\n" +
    '   export DEEPTUTOR_API_BASE="http://127.0.0.1:8001" (serve port)\n' +
    '   export DEEPTUTOR_LOCAL_BIN="deeptutor" (local CLI path, optional)\n' +
    "   Note: do NOT set DEEPTUTOR_SSH_HOST (empty = local mode)\n" +
    "   Verify serve is running: curl http://127.0.0.1:8001/api/v1/system/status\n" +
    "Remote deployment (deeptutor on a server):\n" +
    '   export DEEPTUTOR_SSH_HOST="your-ssh-alias"\n' +
    '   export DEEPTUTOR_API_BASE="http://127.0.0.1:8001" (local tunnel address; port must match the server\'s serve)\n' +
    '   export DEEPTUTOR_REMOTE_BIN="remote-deeptutor-binary-path"\n' +
    '   export DEEPTUTOR_REMOTE_HOME="remote-DEEPTUTOR_HOME-workspace"\n' +
    "   Verify serve is running on the server (ssh to it: curl http://127.0.0.1:8001/api/v1/system/status)\n" +
    "   Verify passwordless SSH login works (ssh alias + BatchMode)\n" +
    'PowerShell users: use $env:VAR="value" instead of export VAR=value.\n' +
    "Restart the agent after configuring.\n"
  );
}

export const CAPABILITIES = [
  "chat",
  "deep_solve",
  "deep_question",
  "deep_research",
  "visualize",
  "math_animator",
  "mastery_path",
] as const;

export const truncate = (s: string, n: number) =>
  s.length > n ? s.slice(0, n) + `\n…[truncated, ${s.length} chars total]` : s;
