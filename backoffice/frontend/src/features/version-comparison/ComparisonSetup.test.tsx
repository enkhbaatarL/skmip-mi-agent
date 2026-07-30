import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  ComparisonSetup,
  validateComparisonRunId
} from "./ComparisonSetup";

describe("ComparisonSetup", () => {
  it("validates trimmed non-blank comparisonRunId up to 255 characters", () => {
    expect(validateComparisonRunId("   ")).toContain("공백");
    expect(validateComparisonRunId("a".repeat(255))).toBe("");
    expect(validateComparisonRunId(` ${"a".repeat(255)} `)).toBe("");
    expect(validateComparisonRunId("a".repeat(256))).toContain("255");
  });

  it("never auto-selects targetMarket", () => {
    render(
      <ComparisonSetup
        comparisonRunId="multi-event-test"
        targetMarket=""
        targetMarketReason=""
        locked={false}
        onComparisonRunIdChange={vi.fn()}
        onTargetMarketChange={vi.fn()}
        onTargetMarketReasonChange={vi.fn()}
        onRegenerate={vi.fn()}
      />
    );
    expect(screen.getAllByRole("radio")).toHaveLength(3);
    screen.getAllByRole("radio").forEach((radio) => {
      expect(radio).not.toBeChecked();
    });
    expect(screen.getByText(/반드시 선택/)).toBeInTheDocument();
  });
});
