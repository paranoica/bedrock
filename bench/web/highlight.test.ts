import { test } from "node:test";
import assert from "node:assert/strict";
import { highlight, snippet } from "./highlight.ts";

test("marks each word of the query", () => {
  assert.deepEqual(highlight("the cat sat", "cat"), { html: "the <mark>cat</mark> sat", marks: 1 });
});

test("is case-insensitive", () => {
  assert.equal(highlight("Cat cat", "cat").marks, 2);
});

test("an empty query marks nothing", () => {
  assert.deepEqual(highlight("text", "  "), { html: "text", marks: 0 });
});

test("a snippet is cut around the first match", () => {
  const text = "a".repeat(100) + " needle " + "b".repeat(100);
  assert.ok(snippet(text, "needle", 20).includes("needle"));
});
