import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ScenarioGroupPresentationResponse } from "../../domain/apiTypes";
import { ScenarioGroupPresentation } from "./ScenarioGroupPresentation";

afterEach(cleanup);

function fixture(
  engineVersion: "v1" | "v3" | "v4"
): ScenarioGroupPresentationResponse {
  return {
    schemaVersion: "v1",
    rendererVersion: "v1",
    scenarioGroupId: 120,
    engineVersion,
    legacy: engineVersion === "v1",
    warnings: [],
    operation: null,
    sections: {
      eventAnalysis: {
        status: "ready",
        evidenceLevel: engineVersion === "v1" ? "limited" : "full",
        contentType: "text/markdown",
        markdown: "## Event <script>alert(1)</script>"
      },
      scenarioDesign: {
        status: "ready",
        evidenceLevel: engineVersion === "v1" ? "limited" : "full",
        dimensionDefinitions: {
          status: "ready",
          items: [
            {
              dimensionId: "d1",
              label: "수급 방향",
              description: "시장 질문",
              rationale: null,
              sourceEventIds: [101],
              modelSupportStatus: null,
              source: null,
              values: [
                {
                  valueId: "d1_v1",
                  label: "상승",
                  description: null,
                  rationale: "저장된 근거",
                  pressureContribution: "bullish",
                  leverStates: []
                }
              ]
            }
          ]
        },
        scenarioTable: {
          status: "ready",
          headers: [{ key: "d1", label: "수급 방향", displayOrder: 1 }],
          rows: [
            {
              scenarioId: 1,
              displayOrder: 1,
              title: "대표 Scenario",
              narrative: "설명",
              scenarioRole: "ceiling",
              baselineYn: "Y",
              pressureTarget: engineVersion === "v1" ? null : "JKM",
              pressureBand: engineVersion === "v1" ? null : "bullish",
              probabilityScore: 20,
              pressureRationale: "저장된 근거",
              cells: { d1: "상승" },
              cellEvidence: {
                d1: {
                  valueId: "d1_v1",
                  valueLabel: "상승",
                  rationale: "저장된 근거",
                  pressureContribution: "bullish",
                  evidenceLevel: engineVersion === "v1" ? "none" : "full"
                }
              }
            }
          ]
        }
      },
      roleSelectionRationale: {
        status: "ready",
        evidenceLevel: engineVersion === "v1" ? "limited" : "full",
        contentType: "text/markdown",
        markdown: "## 대표 Scenario 선택 근거"
      }
    }
  };
}

describe("ScenarioGroupPresentation", () => {
  it.each(["v1", "v3", "v4"] as const)(
    "renders %s with the same three section component structure",
    (version) => {
      const { container } = render(
        <ScenarioGroupPresentation presentation={fixture(version)} />
      );

      expect(screen.getByRole("region", { name: "Event 분석" })).toBeVisible();
      expect(screen.getByRole("region", { name: "Scenario 설계" })).toBeVisible();
      expect(
        screen.getByRole("region", {
          name: "Ceiling/Floor/Mixed 선택 근거"
        })
      ).toBeVisible();
      expect(screen.getByText("대표 Scenario")).toBeVisible();
      expect(container.querySelector("script")).toBeNull();
      expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeVisible();
    }
  );
});
