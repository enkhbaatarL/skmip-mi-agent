import { describe, expect, it } from "vitest";
import {
  judgeComparisonVersion,
  judgeConfirmation,
  judgeCreate,
  judgeSignpost,
  judgeValidation,
  withTransportJudgment
} from "./judgments";
import {
  makeApiResult,
  makeManifest,
  makeResponse
} from "../test/comparisonFixtures";

describe("v1 body judgments", () => {
  it("uses the callback result field for create", () => {
    expect(
      judgeCreate({
        result: "success",
        scenarioGroup: {
          scenarioGroupId: 1,
          title: "group",
          status: "creating",
          stage: "scenario_created"
        },
        table: { headers: [], rows: [] }
      })
    ).toBe("success");
    expect(judgeCreate({ result: "success" })).toBe("success");
    expect(judgeCreate({ result: "failure", reason: "duplicate" })).toBe(
      "error"
    );
  });

  it("uses three-way validation judgment", () => {
    expect(
      judgeValidation({
        result: "success",
        isValid: true,
        scenarioGroup: {
          scenarioGroupId: 1,
          title: "group",
          status: "creating",
          stage: "scenario_validated"
        }
      })
    ).toBe("success");
    expect(
      judgeValidation({
        result: "success",
        isValid: false,
        reason: "not MECE",
        scenarioGroup: {
          scenarioGroupId: 1,
          title: "group",
          status: "creating",
          stage: "scenario_created"
        }
      })
    ).toBe("warning");
    expect(judgeValidation({ result: "failure" })).toBe("error");
    expect(judgeValidation({ result: "success" }, false)).toBe("error");
  });

  it("keeps signpost callback and confirmation wrapper rules separate", () => {
    expect(judgeSignpost({ result: "success" })).toBe("success");
    expect(judgeSignpost({ result: "failure" })).toBe("error");
    expect(
      judgeConfirmation({
        status: "success",
        message: "ok",
        data: { scenarioGroupId: 1, status: "created", stage: "completed" }
      })
    ).toBe("success");
    expect(
      judgeConfirmation({
        status: "success",
        message: "not done",
        data: {
          scenarioGroupId: 1,
          status: "creating",
          stage: "signpost_created"
        }
      })
    ).toBe("error");
  });

  it.each(["timeout", "abort", "network-error"] as const)(
    "never lets a body guess override %s",
    (outcome) => {
      expect(
        withTransportJudgment(outcome, { result: "success" }, () => "success")
      ).toBe("unknown");
    }
  );
});

describe("comparison version judgment", () => {
  it("requires matching apiVersion and ordered lineage", () => {
    const manifest = makeManifest();
    expect(
      judgeComparisonVersion("v2", manifest, makeApiResult(makeResponse("v2")))
    ).toEqual({ judgment: "success", integrityIssues: [] });

    const wrongVersion = judgeComparisonVersion(
      "v2",
      manifest,
      makeApiResult(makeResponse("v3"))
    );
    expect(wrongVersion.judgment).toBe("error");
    expect(wrongVersion.integrityIssues[0]).toContain("API_VERSION_MISMATCH");

    const wrongLineage = judgeComparisonVersion(
      "v2",
      manifest,
      makeApiResult(makeResponse("v2", { eventIds: [202, 101] }))
    );
    expect(wrongLineage.judgment).toBe("error");
    expect(wrongLineage.integrityIssues[0]).toContain(
      "EVENT_LINEAGE_MISMATCH"
    );
  });

  it("treats status=error/data=null as error and timeout as unknown", () => {
    const manifest = makeManifest();
    expect(
      judgeComparisonVersion(
        "v2",
        manifest,
        makeApiResult({ status: "error", message: "failed", data: null })
      ).judgment
    ).toBe("error");
    expect(
      judgeComparisonVersion(
        "v2",
        manifest,
        makeApiResult(makeResponse("v2"), {
          transportStatus: "timeout",
          judgment: "unknown"
        })
      ).judgment
    ).toBe("unknown");
  });
});
