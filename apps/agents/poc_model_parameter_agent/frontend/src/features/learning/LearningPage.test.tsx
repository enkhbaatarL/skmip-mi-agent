import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { jsonResponse, renderWithProviders } from "../../test/render";
import { LearningPage } from "./LearningPage";

describe("LearningPage", () => {
  it("Worker Cycle을 실행하고 Asset Version History 탭을 표시한다", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.startsWith("/api/feedback")) return jsonResponse({ items: [{ feedbackId: "fb-1", runId: "r", tag: "final", source: "result_review", scope: "run", rawText: "x", context: {}, processingStatus: "pending", createdAt: "2028-01-01" }], total: 1 });
      if (path.startsWith("/api/learning/batches") && !init?.method) return jsonResponse({ items: [], total: 0 });
      if (path === "/api/learning/process-pending" && init?.method === "POST") return jsonResponse({ status: "completed", processed: 1, candidateCount: 1 });
      if (path === "/api/assets") return jsonResponse({ items: [{ assetType: "memory", assetKey: "lng", learnable: true, locked: false, activeVersion: 2 }], total: 1 });
      if (path === "/api/assets/memory/lng/versions") return jsonResponse({ items: [{ assetType: "memory", assetKey: "lng", version: 2, learnable: true, locked: false, active: true, createdAt: "2028-01-02", content: "active memory" }], total: 1 });
      throw new Error(`unexpected ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<LearningPage />, { route: "/learning" });
    expect(await screen.findByText("미처리 Final")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Learning Worker 실행" }));
    expect(await screen.findByText(/한 Cycle을 완료했습니다/)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "C · Asset Versions" }));
    expect(await screen.findByRole("heading", { name: "lng" })).toBeInTheDocument();
    expect(await screen.findByText("active memory")).toBeInTheDocument();
  });
});
