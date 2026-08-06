import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { RunDetail } from "../../api/types";
import { jsonResponse, renderWithProviders } from "../../test/render";
import { FinalFeedbackCard } from "./FinalFeedbackCard";

const run: RunDetail = {
  runId: "run-parent", rootRunId: "run-parent", revision: 1, targetMarket: "JKM", eventIds: [101], createdAt: "2028-01-01", status: "completed",
  scenarioCount: 1, proposalCount: 1, interimFeedbackCount: 0, finalFeedbackCount: 0, adjustmentCount: 0,
  assetSnapshot: [{ assetType: "memory", assetKey: "lng", version: 2 }], metadata: { miEventIds: [101], targetMarket: "JKM", comparisonRunId: "cmp" },
  sourceScenarioJson: {}, scenarios: [], proposals: [], revisionChain: [{ runId: "run-parent", revision: 1 }],
};
const proposal = {
  scenarioKey: "scenario-1", parameterCode: "spot_index", parameterName: "현물 지수", domain: "supply", baselinePeak: 100, proposedPeak: 110,
  delta: 10, deltaPct: 10, confidence: .8, warningCount: 0, series: [], trace: [], leverCodes: ["availability"],
};

describe("FinalFeedbackCard", () => {
  it("원문과 Scope를 전송하고 즉시 생성된 Child Revision을 전달한다", async () => {
    const onCreated = vi.fn();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/runs/run-parent/feedback" && init?.method === "POST") return jsonResponse({
        feedback: { feedbackId: "fb-1", runId: "run-parent", resultRunId: "run-child", tag: "final", source: "result_review", scope: "parameter", rawText: "영향 완화", context: {}, processingStatus: "pending", createdAt: "2028-01-02" },
        resultRun: { runId: "run-child", rootRunId: "run-parent", parentRunId: "run-parent", revision: 2, targetMarket: "JKM", eventIds: [101], createdAt: "2028-01-02", status: "completed", assetSnapshot: {}, scenarios: [], revisionChain: [{ runId: "run-parent", revision: 1 }, { runId: "run-child", revision: 2 }] },
      });
      throw new Error(`unexpected ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<FinalFeedbackCard run={run} scenarioKey="scenario-1" proposal={proposal} onCreated={onCreated} />);
    await user.type(screen.getByLabelText("Final Feedback"), "영향 완화");
    await user.click(screen.getByRole("button", { name: "피드백 저장 + Parameter 재생성" }));
    expect(await screen.findByText(/Child Revision을 생성했습니다/)).toBeInTheDocument();
    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ runId: "run-child", revision: 2 }));
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({ scope: "parameter", scenarioKey: "scenario-1", parameterCode: "spot_index", text: "영향 완화" });
  });

  it("이미 Final Feedback이 있으면 재제출을 잠근다", () => {
    renderWithProviders(<FinalFeedbackCard run={{ ...run, hasFinalFeedback: true, finalFeedbackCount: 1 }} scenarioKey="scenario-1" proposal={proposal} onCreated={vi.fn()} />);
    expect(screen.getByRole("button", { name: "피드백 저장 + Parameter 재생성" })).toBeDisabled();
    expect(screen.getByText(/이미 저장되었습니다/)).toBeInTheDocument();
  });

  it("stale 화면의 409 응답은 재제출을 잠그고 변경 없음 안내를 표시한다", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      code: "CONFLICT",
      message: "동일 Revision에는 Final Feedback을 한 번만 제출할 수 있습니다.",
      details: { runId: "run-parent" },
    }, 409)));
    const user = userEvent.setup();
    renderWithProviders(<FinalFeedbackCard run={run} scenarioKey="scenario-1" proposal={proposal} onCreated={vi.fn()} />);

    await user.type(screen.getByLabelText("Final Feedback"), "stale 화면 중복 제출");
    await user.click(screen.getByRole("button", { name: "피드백 저장 + Parameter 재생성" }));

    expect(await screen.findByText(/어떤 값도 변경하지 않았습니다/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "피드백 저장 + Parameter 재생성" })).toBeDisabled();
    expect(screen.getByText(/이미 저장되었습니다/)).toBeInTheDocument();
  });
});
