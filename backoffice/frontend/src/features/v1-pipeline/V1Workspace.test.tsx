import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgentClient } from "../../api/agentClient";
import type {
  EventDetail,
  EventListRow,
  ScenarioGroupPayload,
  ScenarioTable
} from "../../domain/apiTypes";
import { V1Workspace, type V1ClientContext } from "./V1Workspace";

const runtime = {
  agentBaseUrl: "https://agent.example.com",
  userId: 10001,
  timeoutMs: 5_000
};

function eventRow(): EventListRow {
  return {
    miEventId: 77,
    title: "Pipeline Event",
    eventTitle: "",
    oneLineSummary: "summary",
    eventTime: "2026-07-30",
    occurredAt: "2026-07-30T00:00:00Z",
    category: "market",
    eventTypeL1: { id: 1, code: "L1", label: "Supply" },
    eventTypeL2: { id: 12, code: "L2", label: "Outage" },
    newYn: "Y",
    signalYn: "N",
    signalConfidence: null,
    signalReason: null,
    scenarioSuggestYn: "Y",
    scenarioSuggestReason: "recommended",
    tags: [],
    relatedScenarioGroup: null,
    scenarioActionState: {
      type: "create",
      label: "Create",
      disabled: false,
      reason: null
    }
  };
}

function eventDetail(): EventDetail {
  return {
    ...eventRow(),
    keyBullets: [],
    detailAnalysis: "",
    sourceMiRecordIds: [],
    createdAt: "",
    updatedAt: "",
    language: "ko"
  };
}

function group(stage: string): ScenarioGroupPayload {
  return {
    scenarioGroupId: 501,
    miEventId: 77,
    eventTypeL2Id: 12,
    title: "Generated Group",
    summary: null,
    description: "description",
    dimensionSelected: ["period_label"],
    scenarioCount: 1,
    status: stage === "completed" ? "created" : "creating",
    stage
  };
}

function table(title = "Initial scenario", withSignpost = false): ScenarioTable {
  return {
    headers: [{ key: "period_label", label: "기간", displayOrder: 1 }],
    rows: [
      {
        scenarioId: 90001,
        displayOrder: 1,
        title,
        narrative: "narrative",
        cells: { period_label: "2 months" },
        metrics: { probabilityScore: 75, probabilityDelta: 0 },
        baselineYn: "Y",
        signposts: withSignpost
          ? [
              {
                signpostId: 1,
                label: "Signal",
                probabilityDirectionCode: "sup",
                probabilityImpactScore: 12.5,
                signpostReason: "evidence",
                displayOrder: 1,
                strength: "STRONG"
              }
            ]
          : []
      }
    ]
  };
}

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

describe("V1Workspace", () => {
  it("runs create, validation, signpost, latest-detail, confirmation in order", async () => {
    const requests: Array<{ url: string; method: string; body?: unknown }> = [];
    const fetchMock = vi.fn(
      async (urlValue: RequestInfo | URL, init?: RequestInit) => {
        const url = String(urlValue);
        const method = init?.method ?? "GET";
        const body =
          typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
        requests.push({ url, method, body });

        if (url.includes("/events?")) {
          return jsonResponse({
            rows: [eventRow()],
            pagination: {
              page: 1,
              pageSize: 20,
              total: 1,
              hasPrevious: false,
              hasNext: false
            },
            source: {}
          });
        }
        if (url.endsWith("/events/77")) {
          return jsonResponse({
            event: eventDetail(),
            scenarioTemplate: {},
            source: {}
          });
        }
        if (url.endsWith("/scenario-groups/sync")) {
          return jsonResponse({
            result: "success",
            reason: null,
            scenarioGroup: group("scenario_created"),
            table: table(),
            usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30 }
          });
        }
        if (url.endsWith("/validation/sync")) {
          return jsonResponse({
            result: "success",
            isValid: true,
            reason: "valid",
            scenarioGroup: group("scenario_validated"),
            table: body.table
          });
        }
        if (url.endsWith("/signposts/sync")) {
          return jsonResponse({
            result: "success",
            reason: null,
            scenarioGroup: group("signpost_created"),
            table: table(body.table.rows[0].title, true)
          });
        }
        if (
          url.endsWith("/scenario-groups/501") &&
          method.toUpperCase() === "GET"
        ) {
          return jsonResponse({
            scenarioGroup: { ...group("signpost_created"), delYn: "N" },
            table: table("Edited scenario", true),
            scenarioCount: 1,
            signpostCount: 1,
            deletedScenarioCount: 0,
            deletedSignpostCount: 0
          });
        }
        if (url.endsWith("/confirmation")) {
          return jsonResponse({
            status: "success",
            message: "성공",
            data: {
              scenarioGroupId: 501,
              status: "created",
              stage: "completed"
            }
          });
        }
        throw new Error(`unexpected request ${method} ${url}`);
      }
    );
    vi.stubGlobal("fetch", fetchMock);
    const lockChange = vi.fn();
    const recorded: unknown[] = [];
    const createClient = (): V1ClientContext => ({
      runtime,
      client: new AgentClient(runtime, (record) => recorded.push(record))
    });
    const user = userEvent.setup();
    render(
      <V1Workspace
        createClient={createClient}
        onRunLockChange={lockChange}
      />
    );

    await screen.findByText("Pipeline Event");
    await user.click(screen.getByLabelText("77 Event 선택"));
    expect(
      await screen.findAllByText("#77 · Pipeline Event")
    ).not.toHaveLength(0);
    const createButton = await screen.findByRole("button", {
      name: "Create 실행"
    });
    await waitFor(() => expect(createButton).toBeEnabled());
    await user.click(createButton);

    const title = await screen.findByLabelText("1번 Scenario title");
    expect(screen.getAllByText("30").length).toBeGreaterThan(0);
    await user.clear(title);
    await user.type(title, "Edited scenario");
    await user.click(
      screen.getByRole("button", { name: "Validation 실행" })
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Signpost 실행" })).toBeEnabled()
    );
    await user.click(screen.getByRole("button", { name: "Signpost 실행" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", {
          name: "최신 detail 조회"
        })
      ).toBeEnabled()
    );
    expect(screen.getByLabelText("1번 Scenario title")).toBeDisabled();
    await user.click(
      screen.getByRole("button", {
        name: "최신 detail 조회"
      })
    );
    await screen.findByRole("button", {
      name: "Confirmation 승인 및 실행"
    });
    expect(
      requests.filter((request) => request.url.endsWith("/confirmation"))
    ).toHaveLength(0);
    expect(
      screen.getByLabelText("Confirmation request preview raw text")
    ).toHaveTextContent('"userId": 10001');
    await user.click(
      screen.getByRole("button", {
        name: "Confirmation 승인 및 실행"
      })
    );

    expect(await screen.findByText("created/completed")).toBeInTheDocument();
    const postPaths = requests
      .filter((request) => request.method.toUpperCase() === "POST")
      .map((request) => request.url.replace(runtime.agentBaseUrl, ""));
    expect(postPaths).toEqual([
      "/scenario-groups/sync",
      "/scenario-groups/501/validation/sync",
      "/scenario-groups/501/signposts/sync",
      "/scenario-groups/501/confirmation"
    ]);
    const validationRequest = requests.find((request) =>
      request.url.endsWith("/validation/sync")
    );
    expect(validationRequest?.body).toMatchObject({
      userId: 10001,
      table: {
        rows: [{ scenarioId: 90001, displayOrder: 1, title: "Edited scenario" }]
      }
    });
    const confirmationRequest = requests.find((request) =>
      request.url.endsWith("/confirmation")
    );
    expect(confirmationRequest?.body).toMatchObject({
      userId: 10001,
      scenarioGroup: {
        title: "Generated Group",
        summary: null,
        description: "description"
      },
      table: {
        rows: [
          {
            title: "Edited scenario",
            signposts: [{ signpostId: 1, useYn: "Y" }]
          }
        ]
      }
    });
    expect(recorded).toHaveLength(7);
    expect(lockChange).toHaveBeenCalledWith(true);
    await waitFor(() => expect(lockChange).toHaveBeenLastCalledWith(false));
  });

  it("treats validation invalid as warning and gates Signpost on acknowledgment", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (urlValue: RequestInfo | URL) => {
        const url = String(urlValue);
        if (url.includes("/events?")) {
          return jsonResponse({
            rows: [eventRow()],
            pagination: {
              page: 1,
              pageSize: 20,
              total: 1,
              hasPrevious: false,
              hasNext: false
            },
            source: {}
          });
        }
        if (url.endsWith("/events/77")) {
          return jsonResponse({
            event: eventDetail(),
            scenarioTemplate: {},
            source: {}
          });
        }
        if (url.endsWith("/scenario-groups/sync")) {
          return jsonResponse({
            result: "success",
            scenarioGroup: group("scenario_created"),
            table: table()
          });
        }
        return jsonResponse({
          result: "success",
          isValid: false,
          reason: "not MECE",
          scenarioGroup: group("scenario_created"),
          table: table()
        });
      })
    );
    const createClient = () => ({
      runtime,
      client: new AgentClient(runtime)
    });
    const user = userEvent.setup();
    render(
      <V1Workspace
        createClient={createClient}
        onRunLockChange={() => undefined}
      />
    );
    await screen.findByText("Pipeline Event");
    await user.click(screen.getByLabelText("77 Event 선택"));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Create 실행" })).toBeEnabled()
    );
    await user.click(screen.getByRole("button", { name: "Create 실행" }));
    await screen.findByLabelText("1번 Scenario title");
    await user.click(
      screen.getByRole("button", { name: "Validation 실행" })
    );

    expect(await screen.findAllByText("not MECE")).not.toHaveLength(0);
    expect(
      screen.queryByRole("button", { name: "Signpost 실행" })
    ).not.toBeInTheDocument();
    await user.click(
      screen.getAllByRole("button", { name: "확인하고 계속" })[0]
    );
    expect(
      await screen.findByRole("button", { name: "Signpost 실행" })
    ).toBeEnabled();
  });
});
