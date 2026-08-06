import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { jsonResponse, renderWithProviders } from "../../test/render";
import { FeedbackLedgerPage } from "./FeedbackLedgerPage";

describe("FeedbackLedgerPage", () => {
  it("Interim과 Final을 한 원장에 표시하고 원문 Record JSON을 펼친다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [
      { feedbackId: "fb-i", runId: "run-1", revision: 1, tag: "interim", source: "clarification", scope: "run", rawText: "1월부터 2월", context: { eventIds: [101] }, processingStatus: "pending", createdAt: "2028-01-01T00:00:00Z" },
      { feedbackId: "fb-f", runId: "run-1", resultRunId: "run-2", revision: 1, tag: "final", source: "result_review", scope: "parameter", rawText: "현물 영향을 완화", context: { parameterCode: "spot" }, adjustment: { factor: .7 }, processingStatus: "processed", createdAt: "2028-01-02T00:00:00Z" },
    ], total: 2 })));
    const user = userEvent.setup();
    renderWithProviders(<FeedbackLedgerPage />, { route: "/feedback" });
    expect(await screen.findByText("현물 영향을 완화")).toBeInTheDocument();
    expect(screen.getByText("1월부터 2월")).toBeInTheDocument();
    await user.click(screen.getByText(/fb-f · final\/result_review/));
    expect(screen.getByText(/"resultRunId": "run-2"/)).toBeInTheDocument();
  });
});
