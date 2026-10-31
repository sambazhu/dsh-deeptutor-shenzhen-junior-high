import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  buildLedgerPatch,
  buildPracticePrompt,
  findLedgerQuestion,
} from "../src/ledger.ts";
import { apply } from "../src/index.ts";

test("findLedgerQuestion locates a question by id in 02_数学/错题集/题库.json without mutating disk", () => {
  const root = mkdtempSync(join(tmpdir(), "dt-ledger-test-"));
  try {
    const mathDir = join(root, "02_数学", "错题集");
    mkdirSync(mathDir, { recursive: true });
    writeFileSync(
      join(mathDir, "题库.json"),
      JSON.stringify({
        subject: "数学",
        title: "朱秋宇七年级数学错题集",
        questions: [
          {
            id: "MATH-20261016-12",
            topic: "数轴、有理数大小比较、绝对值化简",
            question: "有理数 a < b < 0 < c，化简 |a+c| - |a-b|",
            answer: "-c - b",
          },
        ],
      }),
      "utf8",
    );

    const found = findLedgerQuestion("MATH-20261016-12", { ledgerRoot: root });
    assert.equal(found.subject, "数学");
    assert.equal(found.question.id, "MATH-20261016-12");
    assert.equal(found.question.answer, "-c - b");

    const explainPrompt = buildPracticePrompt(found, "explain", 2);
    assert.match(explainPrompt, /北师大版七年级/);
    assert.match(explainPrompt, /两种不同方法/);

    const variantPrompt = buildPracticePrompt(found, "variant", 2);
    assert.match(variantPrompt, /2 道同类变式练习题/);

    const patch = buildLedgerPatch(found.question.id, {
      explanation: "章节依据：第二章有理数...",
      variant: "变式1：...",
    });
    assert.equal(patch.id, "MATH-20261016-12");
    assert.equal(patch.explanation_source, "deeptutor");
    assert.equal(patch.verified, false);
    assert.equal(patch.explanation, "章节依据：第二章有理数...");
    assert.equal(patch.variant, "变式1：...");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("findLedgerQuestion throws a clear error when question_id does not exist", () => {
  const root = mkdtempSync(join(tmpdir(), "dt-ledger-empty-"));
  try {
    assert.throws(
      () => findLedgerQuestion("MATH-NOT-FOUND", { ledgerRoot: root }),
      /not found in ledger root/,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("apply registers all 4 tools including deeptutor_practice", () => {
  const registered: string[] = [];
  const fakeCtx: any = {
    effect: () => {},
    tools: {
      register: (tool: any) => {
        registered.push(tool.name);
      },
    },
  };
  apply(fakeCtx);
  assert.deepEqual(registered, [
    "deeptutor_run",
    "deeptutor_kb",
    "deeptutor_note",
    "deeptutor_practice",
  ]);
});
