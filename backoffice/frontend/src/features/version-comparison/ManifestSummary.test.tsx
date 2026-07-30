import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { EventDetail } from "../../domain/apiTypes";
import { ComparisonSetup } from "./ComparisonSetup";
import { ManifestSummary } from "./ManifestSummary";

const events = [
  { miEventId: 101, title: "Event 101", eventTitle: "Event 101" },
  { miEventId: 202, title: "Event 202", eventTitle: "Event 202" }
] as EventDetail[];

function LockHarness() {
  const [locked, setLocked] = useState(false);
  const [runId, setRunId] = useState("multi-event-lock-test");
  return (
    <>
      <ComparisonSetup
        comparisonRunId={runId}
        targetMarket="JKM"
        targetMarketReason="fixture"
        locked={locked}
        onComparisonRunIdChange={setRunId}
        onTargetMarketChange={() => undefined}
        onTargetMarketReasonChange={() => undefined}
        onRegenerate={() => setRunId("regenerated")}
      />
      <ManifestSummary
        runtime={{
          agentBaseUrl: "http://127.0.0.1:8001",
          userId: 10001,
          timeoutMs: 10_000
        }}
        selectedEvents={events}
        comparisonRunId={runId}
        targetMarket="JKM"
        targetMarketReason="fixture"
        locked={locked}
        canExecute
        onExecute={() => setLocked(true)}
      />
    </>
  );
}

describe("manifest lock", () => {
  it("locks all setup inputs at the explicit comparison action", async () => {
    const user = userEvent.setup();
    render(<LockHarness />);
    const runIdInput = screen.getByLabelText("comparisonRunId");
    expect(runIdInput).not.toBeDisabled();

    await user.click(screen.getByRole("button", { name: "비교 실행" }));

    expect(runIdInput).toBeDisabled();
    expect(screen.getByRole("button", { name: /고유값 재생성/ })).toBeDisabled();
    expect(screen.getByText("잠김")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "비교 실행" })).toBeDisabled();
  });
});
