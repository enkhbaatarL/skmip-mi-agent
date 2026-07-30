import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeManifest, makeResponse } from "../../test/comparisonFixtures";
import { createVersionStates } from "./types";
import {
  ScenarioComparison,
  scenarioAlignmentKey
} from "./ScenarioComparison";

describe("ScenarioComparison alignment", () => {
  it("uses pressure/role identity instead of each version's array index", () => {
    const versions = createVersionStates();
    const v2 = makeResponse("v2");
    const v3 = makeResponse("v3");
    v3.data!.table.rows.reverse();
    v3.data!.table.rows = v3.data!.table.rows.filter(
      (row) => row.globalPressureBand !== "bearish"
    );
    v3.data!.generationDiagnostics.excludedCandidates = [
      {
        globalPressureBand: "bearish",
        reasonCode: "DUPLICATE",
        reason: "bearish candidate excluded"
      }
    ];
    versions.v2 = { ...versions.v2, status: "success", response: v2 };
    versions.v3 = { ...versions.v3, status: "success", response: v3 };

    render(
      <ScenarioComparison versions={versions} manifest={makeManifest()} />
    );

    expect(
      screen.getByText("bearish: bearish candidate excluded")
    ).toBeInTheDocument();
    expect(
      scenarioAlignmentKey(v2.data!.table.rows[0])
    ).toBe("pressure:strong_bearish");
  });
});
