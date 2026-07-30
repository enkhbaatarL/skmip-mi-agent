import { describe, expect, it } from "vitest";
import {
  connectionFailureGuidance,
  isMixedContentRequest
} from "./connection";

describe("connection diagnostics", () => {
  it("prevents HTTPS frontend to HTTP Agent mixed content", () => {
    expect(
      isMixedContentRequest("http://agent.example.com", "https:")
    ).toBe(true);
    expect(
      isMixedContentRequest("https://agent.example.com", "https:")
    ).toBe(false);
  });

  it("distinguishes HTTP from network/CORS guidance", () => {
    const base = {
      id: "call",
      url: "https://agent.example.com/events",
      method: "GET",
      startedAt: "",
      finishedAt: "",
      elapsedMs: 1,
      judgment: "error" as const
    };
    expect(
      connectionFailureGuidance({
        ...base,
        transportStatus: "http-error",
        httpStatus: 401
      })
    ).toContain("HTTP 401");
    expect(
      connectionFailureGuidance({
        ...base,
        transportStatus: "network-error"
      })
    ).toContain("Network/CORS");
  });
});
