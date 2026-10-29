import { test } from "node:test";
import assert from "node:assert/strict";
import {
  applyChildModePrompt,
  CAPABILITIES,
  getSubjectKbMap,
  resolveSubjectKbs,
  truncate,
} from "../src/config.ts";

test("truncate keeps short strings unchanged", () => {
  assert.equal(truncate("hello", 100), "hello");
});

test("truncate shortens long strings and reports the original length", () => {
  const long = "a".repeat(200);
  const out = truncate(long, 100);
  assert.ok(out.startsWith("a".repeat(100)));
  assert.match(out, /…\[truncated, 200 chars total\]/);
});

test("CAPABILITIES covers the documented learning capabilities", () => {
  assert.deepEqual(CAPABILITIES, [
    "chat",
    "deep_solve",
    "deep_question",
    "deep_research",
    "visualize",
    "math_animator",
    "mastery_path",
  ]);
});

test("resolveSubjectKbs maps 数学 to sz-g7-math-bsd and appends qiuyu-wrongbook", () => {
  assert.deepEqual(resolveSubjectKbs("数学"), ["sz-g7-math-bsd", "qiuyu-wrongbook"]);
  assert.deepEqual(resolveSubjectKbs("math", false), ["sz-g7-math-bsd"]);
});

test("getSubjectKbMap merges valid JSON overrides and ignores invalid JSON", () => {
  const map = getSubjectKbMap('{"英语":"sz-g7-eng-hj"}');
  assert.equal(map["数学"], "sz-g7-math-bsd");
  assert.equal(map["英语"], "sz-g7-eng-hj");
  const fallback = getSubjectKbMap("not-json");
  assert.equal(fallback["数学"], "sz-g7-math-bsd");
});

test("applyChildModePrompt prepends Socratic guard only when enabled and idempotent", () => {
  assert.equal(applyChildModePrompt("化简 |a+c|", false), "化简 |a+c|");
  const guarded = applyChildModePrompt("化简 |a+c|", true);
  assert.match(guarded, /【深圳初一伴读安全约束】/);
  assert.equal(applyChildModePrompt(guarded, true), guarded);
});
