import { describe, expect, it } from "vitest";
import {
  runDeterministicChecks,
  summarizeChecks
} from "./deterministicChecks";
import { makeManifest, makeVersionData } from "../test/comparisonFixtures";

describe("deterministic comparison checks", () => {
  it.each([
    ["v2", 5],
    ["v3", 4],
    ["v4", 3]
  ] as const)("passes fixture evidence for %s", (version, dimensionCount) => {
    const data = makeVersionData(version, { dimensionCount });
    const checks = runDeterministicChecks(version, data, makeManifest());
    expect(summarizeChecks(checks)).toEqual({
      pass: version === "v4" ? 12 : 11,
      warn: 0,
      fail: 0
    });
    expect(
      checks.find((item) => item.id === "probability-sum")?.evidence
    ).toContain("100.0000");
  });

  it("returns literal WARN and FAIL evidence without a semantic score", () => {
    const data = makeVersionData("v4");
    data.table.rows[0].probabilityScore = 10;
    data.table.rows[1].globalPressureBand = "strong_bearish";
    data.table.rows[1].cells = { ...data.table.rows[0].cells };
    data.dimensionDefinitions = data.dimensionDefinitions.slice(0, 2);
    data.table.headers = data.table.headers.slice(0, 2);
    data.table.rows.forEach((row) => {
      row.cells = Object.fromEntries(Object.entries(row.cells).slice(0, 2));
    });
    data.events = data.events.slice(0, 1);
    data.dimensionDefinitions.forEach((dimension) => {
      dimension.sourceEventIds = [101];
      dimension.sourceRefs = dimension.sourceRefs.map((source) => ({
        ...source,
        eventId: 101
      }));
      dimension.values.forEach((value) => {
        value.sourceAssignments = [];
      });
    });
    data.targetMarket = "TTF";

    const checks = runDeterministicChecks("v4", data, makeManifest());
    expect(
      checks.find((item) => item.id === "probability-sum")
    ).toMatchObject({ status: "warn" });
    expect(
      checks.find((item) => item.id === "unique-scenario-combination")
    ).toMatchObject({ status: "fail" });
    expect(
      checks.find((item) => item.id === "unique-pressure-band")
    ).toMatchObject({ status: "fail" });
    expect(checks.find((item) => item.id === "dimension-count")).toMatchObject({
      status: "fail",
      evidence: "실제 dimension 2개"
    });
    expect(
      checks.find((item) => item.id === "event-lineage-coverage")?.evidence
    ).toContain("누락 [202]");
    expect(checks.find((item) => item.id === "target-market")).toMatchObject({
      status: "fail",
      evidence: "manifest JKM, 응답 TTF"
    });
    expect(JSON.stringify(checks)).not.toMatch(/semantic|score|best/i);
  });

  it("fails dimension lineage coverage even when the top-level Event list is complete", () => {
    const data = makeVersionData("v2");
    data.dimensionDefinitions.forEach((dimension) => {
      dimension.sourceEventIds = [101];
      dimension.sourceRefs = dimension.sourceRefs.map((source) => ({
        ...source,
        eventId: 101
      }));
      dimension.values.forEach((value) => {
        value.sourceAssignments = [];
      });
    });

    const checks = runDeterministicChecks("v2", data, makeManifest());

    expect(data.events.map((event) => event.miEventId)).toEqual([101, 202]);
    expect(
      checks.find((item) => item.id === "event-lineage-coverage")
    ).toMatchObject({ status: "fail" });
    expect(
      checks.find((item) => item.id === "event-lineage-coverage")?.evidence
    ).toContain("누락 [202]");
  });

  it("fails when dimension definitions, headers, and row cell keys diverge", () => {
    const data = makeVersionData("v3");
    data.table.headers[0].key = "unknown_header";
    data.table.rows[0].cells.unknown_cell = "value";

    const checks = runDeterministicChecks("v3", data, makeManifest());

    expect(
      checks.find((item) => item.id === "dimension-identifiers")
    ).toMatchObject({ status: "fail" });
  });
});
