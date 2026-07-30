import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type {
  ConfirmationRequest,
  ScenarioGroupDetailResponse,
  TableSyncRequest
} from "../../domain/apiTypes";
import { ConfirmationStep } from "./ConfirmationStep";
import { SignpostStep } from "./SignpostStep";

const table = {
  headers: [{ key: "period", label: "기간", displayOrder: 1 }],
  rows: [
    {
      scenarioId: 1,
      displayOrder: 1,
      title: "Scenario",
      cells: { period: "short" }
    }
  ]
};

describe("destructive v1 step retry confirmation", () => {
  it("requires explicit confirmation before retrying a failed Signpost POST", async () => {
    const onExecute = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const request: TableSyncRequest = { userId: 10001, table };
    const user = userEvent.setup();

    render(
      <SignpostStep
        request={request}
        step={{ status: "error", error: "failed" }}
        onExecute={onExecute}
        onCancel={() => undefined}
      />
    );
    await user.click(screen.getByRole("button", { name: "Signpost 실행" }));

    expect(confirm).toHaveBeenCalled();
    expect(onExecute).not.toHaveBeenCalled();
  });

  it("requires explicit confirmation before retrying a failed Confirmation POST", async () => {
    const onConfirm = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const request: ConfirmationRequest = {
      userId: 10001,
      scenarioGroup: {
        title: "Group",
        summary: null,
        description: null
      },
      table
    };
    const latestDetail: ScenarioGroupDetailResponse = {
      scenarioGroup: {
        scenarioGroupId: 1,
        title: "Group",
        status: "creating",
        stage: "signpost_created"
      },
      table,
      scenarioCount: 1,
      signpostCount: 0,
      deletedScenarioCount: 0,
      deletedSignpostCount: 0
    };
    const user = userEvent.setup();

    render(
      <ConfirmationStep
        request={request}
        latestDetail={latestDetail}
        step={{ status: "error", request, error: "failed" }}
        onPrepare={() => undefined}
        onConfirm={onConfirm}
        onCancel={() => undefined}
      />
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmation 승인 및 실행" })
    );

    expect(confirm).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
