import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgentClient } from "../api/agentClient";
import type { ApiCallRecord } from "../domain/apiCall";
import {
  createRuntimeSnapshot,
  type RuntimeConfig
} from "../domain/runtime";
import {
  AppShell,
  type ConnectionStatus
} from "./AppShell";

const validRuntime: RuntimeConfig = {
  agentBaseUrl: "http://127.0.0.1:8001",
  userId: "10603",
  timeoutSeconds: "1200"
};

const calls: ApiCallRecord[] = [
  {
    id: "call-1",
    url: "http://127.0.0.1:8001/events?page=1",
    method: "GET",
    startedAt: "2026-07-30T00:00:00.000Z",
    finishedAt: "2026-07-30T00:00:00.020Z",
    elapsedMs: 20,
    httpStatus: 200,
    transportStatus: "success",
    judgment: "success",
    parsed: { rows: [{ miEventId: 1 }] },
    rawText: '{"rows":[{"miEventId":1}]}'
  },
  {
    id: "call-2",
    url: "http://127.0.0.1:8001/events/2",
    method: "GET",
    startedAt: "2026-07-30T00:00:01.000Z",
    finishedAt: "2026-07-30T00:00:01.040Z",
    elapsedMs: 40,
    httpStatus: 500,
    transportStatus: "http-error",
    judgment: "error",
    rawText: '{"detail":"failure"}',
    error: "HTTP 500"
  }
];

function createV1Client() {
  const runtime = createRuntimeSnapshot(validRuntime);
  return { runtime, client: new AgentClient(runtime) };
}

const createComparisonClient = createV1Client;

function renderShell(
  overrides: Partial<React.ComponentProps<typeof AppShell>> = {}
) {
  const props: React.ComponentProps<typeof AppShell> = {
    runtimeConfig: validRuntime,
    connectionStatus: "unchecked",
    calls: [],
    runtimeLocked: false,
    createV1Client,
    createComparisonClient,
    onV1RunLockChange: vi.fn(),
    onComparisonRunLockChange: vi.fn(),
    onRuntimeChange: vi.fn(),
    onCheckConnection: vi.fn().mockResolvedValue(undefined),
    onSaveRuntime: vi.fn(),
    onResetRuntime: vi.fn().mockResolvedValue(undefined),
    ...overrides
  };
  return { ...render(<AppShell {...props} />), props };
}

function ConnectionHarness({ shouldSucceed }: { shouldSucceed: boolean }) {
  const [runtime, setRuntime] = useState(validRuntime);
  const [status, setStatus] = useState<ConnectionStatus>("unchecked");

  async function check() {
    setStatus("checking");
    await new Promise((resolve) => window.setTimeout(resolve, 20));
    setStatus(shouldSucceed ? "connected" : "failed");
  }

  return (
    <AppShell
      runtimeConfig={runtime}
      connectionStatus={status}
      calls={[]}
      runtimeLocked={false}
      createV1Client={createV1Client}
      createComparisonClient={createComparisonClient}
      onV1RunLockChange={() => undefined}
      onComparisonRunLockChange={() => undefined}
      onRuntimeChange={setRuntime}
      onCheckConnection={check}
      onSaveRuntime={() => undefined}
      onResetRuntime={async () => undefined}
    />
  );
}

describe("AppShell", () => {
  it("renders the product header, workspace tabs, and Evidence trigger", () => {
    renderShell();
    expect(
      screen.getByRole("heading", { name: "Scenario Comparison" })
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "v1 단일 이벤트" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "v2/v3/v4 비교" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Evidence" })).toBeInTheDocument();
    expect(
      screen.getByLabelText("Authorization (memory only)")
    ).toHaveAttribute("type", "password");
  });

  it("preserves independent local state while switching mounted workspaces", async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole("button", { name: "ID 직접 입력" }));
    const v1EventId = screen.getByLabelText("miEventId");
    await user.type(v1EventId, "12345");
    await user.click(screen.getByRole("tab", { name: "v2/v3/v4 비교" }));
    const comparisonReason = screen.getByLabelText("target market 선택 사유");
    await user.type(comparisonReason, "comparison-only");
    await user.click(screen.getByRole("tab", { name: "v1 단일 이벤트" }));

    expect(screen.getByLabelText("miEventId")).toHaveValue("12345");
    await user.click(screen.getByRole("tab", { name: "v2/v3/v4 비교" }));
    expect(screen.getByLabelText("target market 선택 사유")).toHaveValue(
      "comparison-only"
    );
  });

  it("shows field errors and blocks connection checks for invalid runtime input", async () => {
    const user = userEvent.setup();
    const onCheckConnection = vi.fn().mockResolvedValue(undefined);

    function InvalidHarness() {
      const [runtime, setRuntime] = useState<RuntimeConfig>({
        agentBaseUrl: "",
        userId: "bad-id",
        timeoutSeconds: "0"
      });
      return (
        <AppShell
          runtimeConfig={runtime}
          connectionStatus="unchecked"
          calls={[]}
          runtimeLocked={false}
          createV1Client={createV1Client}
          createComparisonClient={createComparisonClient}
          onV1RunLockChange={() => undefined}
          onComparisonRunLockChange={() => undefined}
          onRuntimeChange={setRuntime}
          onCheckConnection={onCheckConnection}
          onSaveRuntime={() => undefined}
          onResetRuntime={async () => undefined}
        />
      );
    }

    render(<InvalidHarness />);
    await user.click(screen.getByRole("button", { name: "연결 확인" }));

    expect(screen.getByText("Agent Base URL을 입력하세요.")).toBeInTheDocument();
    expect(screen.getByText("userId는 정수여야 합니다.")).toBeInTheDocument();
    expect(
      screen.getByText("Timeout은 0보다 큰 숫자여야 합니다.")
    ).toBeInTheDocument();
    expect(onCheckConnection).not.toHaveBeenCalled();
  });

  it.each([
    [true, "연결됨"],
    [false, "연결 실패"]
  ])(
    "announces loading and final connection state (%s)",
    async (shouldSucceed, finalLabel) => {
      const user = userEvent.setup();
      render(<ConnectionHarness shouldSucceed={shouldSucceed} />);

      await user.click(screen.getByRole("button", { name: "연결 확인" }));
      expect(screen.getByRole("status")).toHaveTextContent("확인 중");
      await waitFor(() =>
        expect(screen.getByRole("status")).toHaveTextContent(finalLabel)
      );
    }
  );

  it("selects an API call and displays its raw JSON in the Evidence Drawer", async () => {
    const user = userEvent.setup();
    renderShell({ calls });

    await user.click(screen.getByRole("button", { name: /Evidence/ }));
    await user.click(screen.getByRole("button", { name: /GET · 200/ }));
    await user.click(screen.getByRole("tab", { name: "Raw 응답" }));

    expect(screen.getByText('{"rows":[{"miEventId":1}]}')).toBeInTheDocument();
  });

  it("shows Evidence workflow/step metadata", async () => {
    const user = userEvent.setup();
    renderShell({
      calls: [
        {
          ...calls[0],
          metadata: { workflow: "comparison", step: "version-create", version: "v2" }
        }
      ]
    });

    await user.click(screen.getByRole("button", { name: /Evidence/ }));
    expect(screen.getByText("comparison/version-create/v2", { exact: false }))
      .toBeInTheDocument();
    expect(screen.getByText("comparison")).toBeInTheDocument();
    expect(screen.getByText("version-create / v2")).toBeInTheDocument();
  });

  it("supports keyboard tab activation and drawer Enter/Escape operation", async () => {
    const user = userEvent.setup();
    renderShell();
    const comparisonTab = screen.getByRole("tab", {
      name: "v2/v3/v4 비교"
    });
    comparisonTab.focus();
    await user.keyboard("{Enter}");
    expect(comparisonTab).toHaveAttribute("aria-selected", "true");

    const evidenceTrigger = screen.getByRole("button", { name: "Evidence" });
    evidenceTrigger.focus();
    await user.keyboard("{Enter}");
    expect(
      screen.getByRole("dialog", { name: "Evidence Drawer" })
    ).toBeInTheDocument();
    await user.tab();
    expect(screen.getByRole("dialog")).toContainElement(
      document.activeElement as HTMLElement
    );
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(evidenceTrigger).toHaveFocus();
  });
});
