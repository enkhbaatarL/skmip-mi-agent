import { RefreshCw } from "lucide-react";

export function generateComparisonRunId(): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 10)
      : Math.random().toString(36).slice(2, 12);
  return `multi-event-${Date.now()}-${random}`;
}

export function validateComparisonRunId(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "comparisonRunId는 공백일 수 없습니다.";
  if (trimmed.length > 255) {
    return "comparisonRunId는 trim 후 255자 이하여야 합니다.";
  }
  return "";
}

interface ComparisonSetupProps {
  comparisonRunId: string;
  locked: boolean;
  onComparisonRunIdChange: (value: string) => void;
  onRegenerate: () => void;
}

export function ComparisonSetup({
  comparisonRunId,
  locked,
  onComparisonRunIdChange,
  onRegenerate
}: ComparisonSetupProps) {
  const runIdError = validateComparisonRunId(comparisonRunId);

  return (
    <section className="comparison-panel" aria-labelledby="comparison-setup-title">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">1. 비교 조건</p>
          <h2 id="comparison-setup-title">비교 실행 조건</h2>
          <p>모든 version은 동일한 Event와 글로벌 LNG pressure 기준으로 비교합니다.</p>
        </div>
      </div>

      <div className="comparison-setup-grid">
        <div className="run-id-field">
          <label className="field">
            comparisonRunId
            <input
              value={comparisonRunId}
              disabled={locked}
              aria-invalid={Boolean(runIdError)}
              aria-describedby={runIdError ? "comparison-run-id-error" : undefined}
              onChange={(event) =>
                onComparisonRunIdChange(event.currentTarget.value)
              }
            />
          </label>
          <button
            className="button secondary"
            type="button"
            disabled={locked}
            onClick={onRegenerate}
          >
            <RefreshCw aria-hidden="true" size={16} />
            고유값 재생성
          </button>
          {runIdError && (
            <span className="field-error" id="comparison-run-id-error">
              {runIdError}
            </span>
          )}
        </div>

      </div>
    </section>
  );
}
