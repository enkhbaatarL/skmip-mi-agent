import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { RunDetail } from "../../api/types";
import { renderWithProviders } from "../../test/render";
import { ScenarioResults } from "./ScenarioResults";

vi.mock("echarts-for-react", () => ({ default: ({ option }: { option: unknown }) => <div data-testid="echarts">{JSON.stringify(option)}</div> }));

const proposal = (scenarioKey: string, code: string, name: string, proposed: number) => ({
  scenarioKey, parameterCode: code, parameterName: name, domain: "demand", baselinePeak: 100, proposedPeak: proposed,
  delta: proposed - 100, deltaPct: proposed - 100, confidence: .9, warningCount: 0,
  series: [{ month: "2028-01", baseline: 100, proposed, delta: proposed - 100, deltaPct: proposed - 100, phase: "event" }],
  trace: [{ step: "event", label: "Event Evidence", summary: `${name} 근거`, status: "applied" as const }], formula: `100 + ${proposed - 100}`,
});

const run: RunDetail = {
  runId: "run-1", revision: 1, targetMarket: "JKM", eventIds: [101], createdAt: "2028-01-01T00:00:00Z", status: "completed",
  scenarioCount: 2, proposalCount: 3, interimFeedbackCount: 0, finalFeedbackCount: 0, adjustmentCount: 0, assetSnapshot: [],
  metadata: { miEventIds: [101], targetMarket: "JKM", comparisonRunId: "cmp" }, sourceScenarioJson: {},
  scenarios: [
    { scenarioKey: "s1", title: "강한 상승", narrative: "수요 증가", probability: 60, declaredPressureBand: "strong_bullish", computedPressureBand: "bullish", pressureScore: 8, pressureConsistency: "warning", dimensions: [{ dimensionId: "cold", valueId: "high" }] },
    { scenarioKey: "s2", title: "균형", narrative: "상쇄", probability: 40, declaredPressureBand: "balanced", computedPressureBand: "balanced", pressureScore: 0, pressureConsistency: "pass", dimensions: [] },
  ],
  proposals: [proposal("s1", "demand_index", "수요 지수", 110), proposal("s1", "risk_index", "위험 지수", 106), proposal("s2", "demand_index", "수요 지수", 100)],
  revisionChain: [{ runId: "run-1", revision: 1 }],
};

describe("ScenarioResults", () => {
  it("Scenario Tab과 Proposal 행 선택에 따라 Plot, Trace, Formula를 전환한다", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ScenarioResults run={run} />);
    expect(screen.getByRole("tab", { name: /강한 상승/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("100 + 10")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "위험 지수 Parameter 선택" }));
    expect(screen.getByText("100 + 6")).toBeInTheDocument();
    expect(screen.getByText("위험 지수 근거")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /균형/ }));
    expect(screen.getByText("100 + 0")).toBeInTheDocument();
    expect(screen.getByTestId("echarts")).toHaveTextContent("Proposed");
  });
});
