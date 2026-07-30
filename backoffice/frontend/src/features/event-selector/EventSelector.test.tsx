import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgentClient } from "../../api/agentClient";
import type {
  EventDetail,
  EventListRow
} from "../../domain/apiTypes";
import { EventSelector } from "./EventSelector";

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
    eventTypeL1: { id: 1, code: "L1", label: "L1 label" },
    eventTypeL2: { id: 2, code: "L2", label: "L2 label" },
    newYn: "Y",
    signalYn: "N",
    signalConfidence: null,
    signalReason: null,
    scenarioSuggestYn: "Y",
    scenarioSuggestReason: "recommended",
    tags: ["supply"],
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
    keyBullets: ["bullet"],
    detailAnalysis: "analysis without explicit market marker",
    sourceMiRecordIds: [],
    createdAt: "",
    updatedAt: "",
    language: "ko"
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

function SingleHarness({ client }: { client: AgentClient }) {
  const [selected, setSelected] = useState<EventDetail[]>([]);
  return (
    <EventSelector
      mode="single"
      selectedEvents={selected}
      onChange={setSelected}
      client={client}
    />
  );
}

describe("EventSelector", () => {
  it("loads the list, fetches detail, and enforces one selected Event", async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL) => {
      const path = String(url);
      if (path.endsWith("/events/11")) {
        return jsonResponse({
          event: eventDetail(11),
          scenarioTemplate: {},
          source: {}
        });
      }
      if (path.endsWith("/events/12")) {
        return jsonResponse({
          event: eventDetail(12),
          scenarioTemplate: {},
          source: {}
        });
      }
      return jsonResponse({
        rows: [eventRow(11), eventRow(12)],
        pagination: {
          page: 1,
          pageSize: 20,
          total: 2,
          hasPrevious: false,
          hasNext: false
        },
        source: {}
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<SingleHarness client={new AgentClient(runtime)} />);

    await screen.findByText("Event 11");
    await user.click(screen.getByLabelText("11 Event 선택"));
    expect(await screen.findByText("#11 · Event 11")).toBeInTheDocument();
    await user.click(screen.getByLabelText("12 Event 선택"));
    expect(await screen.findByText("#12 · Event 12")).toBeInTheDocument();
    expect(screen.queryByText("#11 · Event 11")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "시장 영향" })).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/events/12"))
    ).toHaveLength(1);
  });

  it("preserves a prior selection when list loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("CORS blocked"))
    );
    render(
      <EventSelector
        mode="single"
        selectedEvents={[eventDetail(21)]}
        onChange={vi.fn()}
        client={new AgentClient(runtime)}
      />
    );

    expect(screen.getByText("#21 · Event 21")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("CORS blocked")
    );
    expect(screen.getByText("#21 · Event 21")).toBeInTheDocument();
  });

  it("preserves scenarioTemplate/source and renders template market impact", async () => {
    const onChange = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn((url: RequestInfo | URL) => {
        if (String(url).endsWith("/events/41")) {
          return jsonResponse({
            event: eventDetail(41),
            scenarioTemplate: {
              templateChecksum: "checksum-41",
              lngPriceImpactExamples: "JKM +12%, TTF +8%"
            },
            source: { provider: "mi-db" }
          });
        }
        return jsonResponse({
          rows: [eventRow(41)],
          pagination: {
            page: 1,
            pageSize: 20,
            total: 1,
            hasPrevious: false,
            hasNext: false
          },
          source: {}
        });
      })
    );
    const user = userEvent.setup();
    const { rerender } = render(
      <EventSelector
        mode="single"
        selectedEvents={[]}
        onChange={onChange}
        client={new AgentClient(runtime)}
      />
    );

    await screen.findByText("Event 41");
    await user.click(screen.getByLabelText("41 Event 선택"));
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const selected = onChange.mock.calls[0][0] as EventDetail[];
    expect(selected[0]).toMatchObject({
      scenarioTemplate: {
        templateChecksum: "checksum-41",
        lngPriceImpactExamples: "JKM +12%, TTF +8%"
      },
      source: { provider: "mi-db" }
    });

    rerender(
      <EventSelector
        mode="single"
        selectedEvents={selected}
        onChange={onChange}
        client={new AgentClient(runtime)}
      />
    );
    expect(screen.getByText("JKM +12%, TTF +8%")).toBeInTheDocument();
  });

  it("keeps multi selection unique and preserves direct-input order", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: RequestInfo | URL) => {
        const match = String(url).match(/\/events\/(\d+)$/);
        if (match) {
          return jsonResponse({
            event: eventDetail(Number(match[1])),
            scenarioTemplate: {},
            source: {}
          });
        }
        return jsonResponse({
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
    const user = userEvent.setup();

    function MultiHarness() {
      const [selected, setSelected] = useState<EventDetail[]>([]);
      return (
        <EventSelector
          mode="multi"
          selectedEvents={selected}
          onChange={setSelected}
          client={new AgentClient(runtime)}
        />
      );
    }

    render(<MultiHarness />);
    await user.click(screen.getByRole("button", { name: "ID 직접 입력" }));
    const input = screen.getByLabelText("miEventId");
    await user.type(input, "31");
    await user.click(screen.getByRole("button", { name: "상세 조회 후 선택" }));
    await screen.findByText("#31 · Event 31");
    await user.clear(input);
    await user.type(input, "32");
    await user.click(screen.getByRole("button", { name: "상세 조회 후 선택" }));
    await screen.findByText("#32 · Event 32");

    const cards = screen.getAllByRole("article");
    expect(cards[0]).toHaveTextContent("#31");
    expect(cards[1]).toHaveTextContent("#32");
    await user.clear(input);
    await user.type(input, "31");
    await user.click(screen.getByRole("button", { name: "상세 조회 후 선택" }));
    expect(screen.getByRole("alert")).toHaveTextContent("이미 선택한");
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });
});
