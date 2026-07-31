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

  it("does not render target market controls", () => {
    render(
      <ComparisonSetup
        comparisonRunId="multi-event-test"
        locked={false}
        onComparisonRunIdChange={vi.fn()}
        onRegenerate={vi.fn()}
      />
    );
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.queryByText(/targetMarket/)).not.toBeInTheDocument();
  });
});
