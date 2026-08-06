import type { ReactNode } from "react";

type Tone = "neutral" | "info" | "success" | "warning" | "error" | "demand" | "supply";

const toneForStatus = (status: string): Tone => {
  const value = status.toLowerCase();
  if (["completed", "success", "healthy", "active", "applied", "pass", "passed", "connected"].includes(value)) return "success";
  if (["warning", "pending", "processing", "retry", "review"].includes(value)) return "warning";
  if (["error", "failed", "conflict", "rejected", "unhealthy"].includes(value)) return "error";
  if (["demand", "bullish", "strong_bullish"].includes(value)) return "demand";
  if (["supply", "bearish", "strong_bearish"].includes(value)) return "supply";
  return "neutral";
};

export function StatusBadge({ children, tone, title }: { children: ReactNode; tone?: Tone; title?: string }) {
  const inferred = typeof children === "string" ? toneForStatus(children) : "neutral";
  return <span className={`badge badge--${tone ?? inferred}`} title={title}>{children}</span>;
}
