import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { runDeterministicChecks } from "../../domain/deterministicChecks";
import {
  makeManifest,
  makeResponse
} from "../../test/comparisonFixtures";
import { createVersionStates } from "./types";
import { OverviewComparison } from "./OverviewComparison";

describe("OverviewComparison", () => {
  it("shows 판정 불가 for fewer than two successes without hiding success data", () => {
    const manifest = makeManifest();
    const response = makeResponse("v2");
    const versions = createVersionStates();
    versions.v2 = {
      ...versions.v2,
      status: "success",
      response,
      elapsedMs: 100
    };
    versions.v3 = { ...versions.v3, status: "error", error: "v3 failed" };
    versions.v4 = { ...versions.v4, status: "unknown", error: "timeout" };
    const checks = {
      v2: runDeterministicChecks("v2", response.data ?? undefined, manifest),
      v3: [],
      v4: []
    };

    render(
      <OverviewComparison
        versions={versions}
        checks={checks}
      />
    );

    expect(screen.getByText("비교 판정 불가")).toBeInTheDocument();
    expect(screen.getByText("#2 · v2 fixture")).toBeInTheDocument();
    expect(screen.getByText("Global LNG pressure")).toBeInTheDocument();
    expect(screen.getByText(/PASS 11/)).toBeInTheDocument();
  });
});
