import { screen } from "@testing-library/react";
import { vi } from "vitest";
import { jsonResponse, renderWithProviders } from "../../test/render";
import { RunHistoryPage } from "./RunHistoryPage";

describe("RunHistoryPage", () => {
  it("Revision, Parent, Feedback, Adjustment, Asset Snapshot을 렌더링한다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ items: [{
      runId: "run-r2", rootRunId: "run-r1", parentRunId: "run-r1", revision: 2, comparisonRunId: "cmp", targetMarket: "JKM", eventIds: [101, 202],
      createdAt: "2028-01-02T00:00:00Z", status: "completed", scenarioCount: 3, proposalCount: 6, interimFeedbackCount: 2, finalFeedbackCount: 0,
      adjustmentCount: 1, assetVersions: { "memory:lng": { assetType: "memory", assetKey: "lng", version: 2 } },
    }], total: 1 })));
    renderWithProviders(<RunHistoryPage />, { route: "/runs" });
    expect(await screen.findByRole("link", { name: "run-r2" })).toHaveAttribute("href", "/runs/run-r2");
    expect(screen.getByText("run-r1")).toBeInTheDocument();
    expect(screen.getByText("2 / 0")).toBeInTheDocument();
    expect(screen.getByText("lng@2")).toBeInTheDocument();
  });
});
