import type { LlmUsage } from "./apiTypes";

export function totalTokens(
  usage: LlmUsage | null | undefined
): number | undefined {
  const value = usage?.totalTokens ?? usage?.total_tokens;
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : undefined;
}
