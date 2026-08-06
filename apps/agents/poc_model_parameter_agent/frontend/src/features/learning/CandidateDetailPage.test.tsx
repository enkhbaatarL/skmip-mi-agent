import { Route, Routes } from "react-router-dom";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { jsonResponse, renderWithProviders } from "../../test/render";
import { CandidateDetailPage } from "./CandidateDetailPage";

describe("CandidateDetailPage", () => {
  it("Base Version Conflict 409를 무변경 메시지로 표시한다", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/learning/candidates/c-1" && !init?.method) return jsonResponse({
        candidateId: "c-1", sourceFeedbackId: "fb-1", sourceRunId: "run-1", sourceTag: "final", sourceFeedbackText: "기본 안내를 추가",
        targetType: "memory", targetAssetKey: "lng_memory", baseVersion: 1, proposedVersion: 2, changeLine: "+ 안내", diff: "+ 새로운 안내",
        confidence: .9, evaluations: [{ name: "schema", passed: true }], status: "pending",
      });
      if (String(input) === "/api/learning/candidates/c-1/approve") return jsonResponse({ detail: { code: "VERSION_CONFLICT", message: "stale" } }, 409);
      throw new Error(`unexpected ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<Routes><Route path="/learning/candidates/:candidateId" element={<CandidateDetailPage />} /></Routes>, { route: "/learning/candidates/c-1" });
    await user.click(await screen.findByRole("button", { name: "Candidate 승인" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("어떤 Asset도 변경되지 않았습니다");
  });
});
