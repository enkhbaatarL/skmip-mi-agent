import { describe, expect, it, vi } from "vitest";
import {
  DEFAULT_RUNTIME_CONFIG,
  type RuntimeConfig
} from "../../domain/runtime";
import {
  RUNTIME_STORAGE_KEY,
  loadRuntimeConfig,
  resolveRuntimeConfig,
  saveRuntimeConfig
} from "./runtimeStorage";

describe("runtimeStorage", () => {
  it("persists only Base URL, userId, and timeout, never secret fields", () => {
    const config = {
      agentBaseUrl: " https://agent.example.com/prefix/ ",
      userId: "10603",
      timeoutSeconds: "1200",
      authorization: "Bearer real-secret",
      token: "token-secret",
      password: "password-secret",
      cookie: "cookie-secret"
    } as RuntimeConfig & Record<string, string>;

    saveRuntimeConfig(config);

    const saved = localStorage.getItem(RUNTIME_STORAGE_KEY);
    expect(saved).not.toContain("real-secret");
    expect(saved).not.toContain("token-secret");
    expect(saved).not.toContain("password-secret");
    expect(saved).not.toContain("cookie-secret");
    expect(JSON.parse(saved ?? "")).toEqual({
      agentBaseUrl: "https://agent.example.com/prefix",
      userId: "10603",
      timeoutSeconds: "1200"
    });
  });

  it("recovers malformed localStorage JSON to defaults", () => {
    localStorage.setItem(RUNTIME_STORAGE_KEY, "{not-json");
    expect(loadRuntimeConfig()).toEqual(DEFAULT_RUNTIME_CONFIG);
  });

  it("resolves Base URL in user, storage, public config, build, fallback order", async () => {
    localStorage.setItem(
      RUNTIME_STORAGE_KEY,
      JSON.stringify({
        agentBaseUrl: "https://stored.example/prefix/",
        userId: "9",
        timeoutSeconds: "20"
      })
    );
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ agentBaseUrl: "https://config.example/" }), {
        status: 200
      })
    );

    await expect(
      resolveRuntimeConfig({
        userInput: { agentBaseUrl: " https://user.example/path/ " },
        fetcher
      })
    ).resolves.toMatchObject({ agentBaseUrl: "https://user.example/path" });
    expect(fetcher).not.toHaveBeenCalled();

    await expect(resolveRuntimeConfig({ fetcher })).resolves.toMatchObject({
      agentBaseUrl: "https://stored.example/prefix"
    });

    localStorage.removeItem(RUNTIME_STORAGE_KEY);
    await expect(resolveRuntimeConfig({ fetcher })).resolves.toMatchObject({
      agentBaseUrl: "https://config.example"
    });

    const missingConfig = vi.fn().mockResolvedValue(new Response("", { status: 404 }));
    await expect(
      resolveRuntimeConfig({
        fetcher: missingConfig,
        buildTimeBaseUrl: "https://build.example/base/"
      })
    ).resolves.toMatchObject({ agentBaseUrl: "https://build.example/base" });

    await expect(
      resolveRuntimeConfig({ fetcher: missingConfig, buildTimeBaseUrl: "" })
    ).resolves.toMatchObject({
      agentBaseUrl: "http://127.0.0.1:8001"
    });
  });
});
