import { describe, expect, it } from "vitest";
import { totalTokens } from "./tokenUsage";

describe("LLM usage boundary", () => {
  it("supports both backend snake_case and legacy camelCase counters", () => {
    expect(totalTokens({ total_tokens: 30 })).toBe(30);
    expect(totalTokens({ totalTokens: 40 })).toBe(40);
    expect(totalTokens(null)).toBeUndefined();
  });
});
