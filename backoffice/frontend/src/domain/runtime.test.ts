import { describe, expect, it } from "vitest";
import {
  DEFAULT_TIMEOUT_SECONDS,
  createRuntimeSnapshot,
  normalizeBaseUrl,
  validateRuntimeConfig,
  type RuntimeConfig
} from "./runtime";

const validConfig: RuntimeConfig = {
  agentBaseUrl: "https://agent.example.com/prefix",
  userId: "10603",
  timeoutSeconds: String(DEFAULT_TIMEOUT_SECONDS)
};

describe("runtime domain", () => {
  it("trims whitespace and trailing slashes while preserving a path prefix", () => {
    expect(
      normalizeBaseUrl("  https://agent.example.com/ingress/prefix///  ")
    ).toBe("https://agent.example.com/ingress/prefix");
    expect(normalizeBaseUrl("https://agent.example.com")).toBe(
      "https://agent.example.com"
    );
  });

  it("validates integer userId and positive timeout", () => {
    expect(validateRuntimeConfig(validConfig)).toEqual({});
    expect(
      validateRuntimeConfig({
        ...validConfig,
        userId: "10.5",
        timeoutSeconds: "0"
      })
    ).toMatchObject({
      userId: expect.stringContaining("정수"),
      timeoutSeconds: expect.stringContaining("0보다 큰")
    });
  });

  it("creates an immutable millisecond snapshot with a 1200 second default", () => {
    const snapshot = createRuntimeSnapshot({
      ...validConfig,
      authorization: "  Bearer memory-secret  "
    });
    expect(snapshot.timeoutMs).toBe(1_200_000);
    expect(snapshot.agentBaseUrl).toBe("https://agent.example.com/prefix");
    expect(snapshot.authorization).toBe("Bearer memory-secret");
    expect(Object.isFrozen(snapshot)).toBe(true);
  });
});
