import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgentClient } from "../../api/agentClient";
import type { EventDetail, EventListRow } from "../../domain/apiTypes";
import { makeResponse } from "../../test/comparisonFixtures";
import { ComparisonWorkspace } from "./ComparisonWorkspace";

const runtime = {
  agentBaseUrl: "https://agent.example.com",
  userId: 10001,
  timeoutMs: 5_000
};

function eventRow(id: number): EventListRow {
  return {
    miEventId: id,
    title: `Event ${id}`,
    eventTitle: "",
    oneLineSummary: `summary ${id}`,
    eventTime: "2026-07-30",
    occurredAt: "2026-07-30T00:00:00Z",
    category: "market",
    eventTypeL1: { id: 1, code: "L1", label: "L1" },
    eventTypeL2: { id: 2, code: "L2", label: "L2" },
    newYn: "Y",
    signalYn: "N",
    signalConfidence: null,
    signalReason: null,
    scenarioSuggestYn: "Y",
    scenarioSuggestReason: "fixture",
    tags: [],
    relatedScenarioGroup: null,
    scenarioActionState: {
      type: "create",
      label: "create",
      disabled: false,
      reason: null
    }
  };
}

function eventDetail(id: number): EventDetail {
  return {
    ...eventRow(id),
    keyBullets: [],
    detailAnalysis: "",
    sourceMiRecordIds: [],
    createdAt: "",
    updatedAt: "",
    language: "ko"
  };
}

function response(body: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

describe("ComparisonWorkspace", () => {
  it("locks the manifest at execution and completes the three version run", async () => {
    const postPaths: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const detailMatch = url.match(/\/events\/(\d+)$/);
        if (detailMatch) {
          return response({
            event: eventDetail(Number(detailMatch[1])),
            scenarioTemplate: {},
            source: {}
          });
        }
        const versionMatch = url.match(/\/(v[234])\/scenario-groups\/sync$/);
        if (versionMatch) {
          const version = versionMatch[1] as "v2" | "v3" | "v4";
          postPaths.push(version);
          expect(JSON.parse(String(init?.body))).toEqual({
            miEventIds: [101],
            userId: 10001
          });
          return response(makeResponse(version, { eventIds: [101] }));
        }
        return response({
          rows: [],
          pagination: {
            page: 1,
            pageSize: 20,
            total: 0,
            hasPrevious: false,
            hasNext: false
          },
          source: {}
        });
      })
    );
    const onRunLockChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ComparisonWorkspace
        createClient={() => ({
          runtime,
          client: new AgentClient(runtime)
        })}
        onRunLockChange={onRunLockChange}
      />
    );

    await user.click(screen.getByRole("button", { name: "ID 직접 입력" }));
    const eventIdInput = screen.getByLabelText("miEventId");
    for (const id of ["101"]) {
      await user.clear(eventIdInput);
      await user.type(eventIdInput, id);
      await user.click(
        screen.getByRole("button", { name: "상세 조회 후 선택" })
      );
      await screen.findByRole("button", {
        name: `${id} Event 선택 해제`
      });
    }
    await user.click(screen.getByRole("button", { name: "비교 실행" }));

    expect(eventIdInput).toBeDisabled();
    await waitFor(() => expect(postPaths).toEqual(["v2", "v3", "v4"]));
    await waitFor(() =>
      expect(screen.getAllByText("성공").length).toBeGreaterThanOrEqual(3)
    );
    expect(onRunLockChange).toHaveBeenCalledWith(true);
    expect(onRunLockChange).toHaveBeenLastCalledWith(false);
  });
});
