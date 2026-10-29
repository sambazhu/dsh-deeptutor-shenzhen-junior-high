/**
 * Learning Ledger (朱秋宇初一学习台账) read-only bridge for dsh-deeptutor.
 *
 * Principle:
 *   - The Learning Ledger is the single source of truth.
 *   - This module ONLY reads `<subject_dir>/错题集/题库.json` from LEDGER_ROOT
 *     and formats structured patches for the DSH agent / ledger skill to write back.
 *   - All generated explanations/variants are marked with:
 *       explanation_source: "deeptutor"
 *       verified: false
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { LEDGER_ROOT } from "./config.ts";

export interface LedgerQuestion {
  id: string;
  date?: string;
  source?: string;
  type?: string;
  topic?: string;
  question: string;
  question_display?: string;
  question_images?: string[];
  blank_lines?: number;
  answer?: string;
  explanation?: string;
  explanation_source?: string;
  verified?: boolean | string;
  mistake_reason?: string;
  variant?: string;
  variant_answer?: string;
  status?: string;
}

export interface FoundLedgerQuestion {
  subject: string;
  subjectDir: string;
  ledgerFile: string;
  bankTitle: string;
  question: LedgerQuestion;
}

export type LedgerQuestionPatch = Record<string, string | boolean>;

export const SUBJECT_DIRECTORIES: Array<{
  subject: string;
  dir: string;
  prefixes: string[];
}> = [
  { subject: "语文", dir: "01_语文", prefixes: ["CHN-", "YW-"] },
  { subject: "数学", dir: "02_数学", prefixes: ["MATH-", "SX-"] },
  { subject: "英语", dir: "03_英语", prefixes: ["ENG-", "YY-"] },
  { subject: "地理", dir: "04_地理", prefixes: ["GEO-", "DL-"] },
  { subject: "历史", dir: "05_历史", prefixes: ["HIS-", "LS-"] },
  { subject: "生物", dir: "06_生物", prefixes: ["BIO-", "SW-"] },
  { subject: "道法", dir: "07_道法", prefixes: ["MOR-", "POL-", "DF-"] },
];

/**
 * Find a wrong-question record by `questionId` across the Learning Ledger's `题库.json` files.
 * Read-only: never mutates the ledger on disk.
 */
export function findLedgerQuestion(
  questionId: string,
  opts: { ledgerRoot?: string; subject?: string } = {},
): FoundLedgerQuestion {
  const root = opts.ledgerRoot?.trim() || LEDGER_ROOT;
  const targetId = questionId.trim();
  if (!targetId) {
    throw new Error("question_id must not be empty");
  }

  const upper = targetId.toUpperCase();
  const orderedDirs = [...SUBJECT_DIRECTORIES].sort((a, b) => {
    const aMatch =
      (opts.subject && a.subject === opts.subject.trim()) ||
      a.prefixes.some((p) => upper.startsWith(p));
    const bMatch =
      (opts.subject && b.subject === opts.subject.trim()) ||
      b.prefixes.some((p) => upper.startsWith(p));
    return (bMatch ? 1 : 0) - (aMatch ? 1 : 0);
  });

  const checkedFiles: string[] = [];
  for (const entry of orderedDirs) {
    const file = join(root, entry.dir, "错题集", "题库.json");
    if (!existsSync(file)) continue;
    checkedFiles.push(file);
    let parsed: any;
    try {
      parsed = JSON.parse(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    const questions: LedgerQuestion[] = Array.isArray(parsed?.questions)
      ? parsed.questions
      : [];
    const hit = questions.find((q) => q && String(q.id).trim() === targetId);
    if (hit) {
      return {
        subject: String(parsed?.subject || entry.subject),
        subjectDir: entry.dir,
        ledgerFile: file,
        bankTitle: String(parsed?.title || `${entry.subject}错题集`),
        question: hit,
      };
    }
  }

  throw new Error(
    `Question "${targetId}" not found in ledger root "${root}" (checked ${checkedFiles.length} 题库.json files)`,
  );
}

/** Build a curriculum-grounded prompt for `deep_solve` (explanation) or `deep_question` (variants). */
export function buildPracticePrompt(
  found: FoundLedgerQuestion,
  kind: "explain" | "variant",
  numVariants = 2,
): string {
  const q = found.question;
  const headerLines = [
    `【深圳初一学习台账 · 错题靶向辅导】`,
    `- 学生：深圳市石厦中学 七年级（初一）`,
    `- 学科：${found.subject}（数学使用北师大版七年级上册 2024 新课标教材）`,
    `- 错题编号：${q.id}`,
    q.source ? `- 来源：${q.source}` : "",
    q.type ? `- 题型：${q.type}` : "",
    q.topic ? `- 知识点（topic）：${q.topic}` : "",
    "",
    `### 原题题干`,
    q.question,
  ].filter(Boolean);

  if (q.answer) {
    headerLines.push("", `### 台账已记录参考答案`, q.answer);
  }
  if (q.mistake_reason) {
    headerLines.push("", `### 错因与复盘重点`, q.mistake_reason);
  }
  if (q.explanation && kind === "variant") {
    headerLines.push("", `### 原题已有解析参考`, q.explanation);
  }

  if (kind === "explain") {
    headerLines.push(
      "",
      `### 任务要求（deep_solve 教材对齐精讲）`,
      `1. **教材章节定位**：请先检索知识库（如 sz-g7-math-bsd），明确指出本题对应北师大版七年级教材的具体章、节名称及核心概念定理（不要使用超纲方法）。`,
      `2. **分步推导**：用适合初一（13岁）学生理解的清晰步骤写出完整解题过程。`,
      `3. **双方法交叉核验（台账硬性要求）**：数学解答必须使用**两种不同方法**（如代数法 + 特殊值代入法 / 数轴几何意义法 / 逆向代入法）交叉验证最终结论一致。`,
      `4. **避坑口诀**：总结 1–2 句针对本题错因的考场防错口诀。`,
    );
  } else {
    headerLines.push(
      "",
      `### 任务要求（deep_question 同考点变式巩固）`,
      `1. 请围绕原题知识点「${q.topic || found.subject}」及对应教材章节，设计 **${numVariants} 道同类变式练习题**（难度梯度：第 1 道同水平巩固，第 2 道微调条件或逆向设问防粗心）。`,
      `2. 严禁超纲（控制在深圳七年级期中/期末真题难度范围内）。`,
      `3. 每道变式题请依次给出：【变式题干】、【参考答案】、【简要解析与双方法核验结果】，以便直接整理进台账的 \`variant\` 字段并导出 Word 错题本。`,
    );
  }

  return headerLines.join("\n");
}

/** Construct the structured patch object for `题库.json` write-back. */
export function buildLedgerPatch(
  questionId: string,
  outputs: { explanation?: string; variant?: string },
): LedgerQuestionPatch {
  const patch: LedgerQuestionPatch = {
    id: questionId,
    explanation_source: "deeptutor",
    verified: false,
  };
  if (outputs.explanation && outputs.explanation.trim()) {
    patch.explanation = outputs.explanation.trim();
  }
  if (outputs.variant && outputs.variant.trim()) {
    patch.variant = outputs.variant.trim();
  }
  return patch;
}
