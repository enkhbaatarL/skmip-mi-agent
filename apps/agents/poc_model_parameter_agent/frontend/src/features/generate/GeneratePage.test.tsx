import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { GeneratePage } from "./GeneratePage";
import { jsonResponse, renderWithProviders } from "../../test/render";

const scenario = {
  groupTitle: "테스트 Scenario",
  eventImpactFacts: [{ eventId: 101, timing: "다가오는 동절기 후반" }],
  scenarios: [{ title: "Scenario A", dimensionValues: {} }],
};

describe("GeneratePage", () => {
  it("API Example을 불러오고 Required Clarification 전에는 실행을 잠근다", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/examples") return jsonResponse({ items: [
        { id: "example1", label: "예시 1", metadata: { miEventIds: [101, 202], targetMarket: "JKM", comparisonRunId: "cmp-1" }, scenarioJson: scenario },
        { id: "example2", label: "예시 2", metadata: { miEventIds: [303, 404], targetMarket: "JKM", comparisonRunId: "cmp-2" }, scenarioJson: scenario },
        { id: "example3", label: "예시 3 (질의 발생)", metadata: { miEventIds: [101, 202], targetMarket: "JKM", comparisonRunId: "cmp-3" }, scenarioJson: scenario },
      ], total: 3 });
      if (path === "/api/plans" && init?.method === "POST") return jsonResponse({
        planSteps: Array.from({ length: 9 }, (_, index) => ({ stepId: `step_${index + 1}`, label: `단계 ${index + 1}`, status: "pending" })),
        validationReport: { status: "warning", errorCount: 0, warningCount: 1, messages: [{ level: "warning", code: "TIMING_AMBIGUOUS", message: "Timing 확인 필요" }] },
        clarifications: [{ questionId: "timing-101", question: "Event 101 Timing 월 범위", required: true, kind: "single_choice", choices: [{ choiceId: "winter-late", label: "1월~2월" }], allowText: true }],
        assumptions: ["월 단위 계산"], assetSnapshot: [{ assetType: "memory", assetKey: "default", version: 2 }], canRun: false,
      });
      throw new Error(`unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<GeneratePage />, { route: "/generate" });

    await user.click(await screen.findByRole("button", { name: "예시 3 (질의 발생) 불러오기" }));
    expect(screen.getByLabelText("miEventIds required")).toHaveValue("101, 202");
    expect((screen.getByLabelText("Scenario JSON") as HTMLTextAreaElement).value).toContain("다가오는 동절기 후반");
    await user.click(screen.getByRole("button", { name: "JSON 검증" }));
    expect(screen.getByText(/JSON Syntax가 유효합니다/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "계획 생성" }));

    expect(await screen.findByRole("heading", { name: "Plan Preview" })).toBeInTheDocument();
    const runButton = screen.getByRole("button", { name: "Parameter 생성" });
    expect(runButton).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: "1월~2월" }));
    await waitFor(() => expect(runButton).toBeEnabled());
  });
});
