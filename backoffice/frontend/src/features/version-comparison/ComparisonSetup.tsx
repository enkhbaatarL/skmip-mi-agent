import { RefreshCw } from "lucide-react";
import type { TargetMarket } from "../../domain/apiTypes";

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
  targetMarket: TargetMarket | "";
  targetMarketReason: string;
  locked: boolean;
  onComparisonRunIdChange: (value: string) => void;
  onTargetMarketChange: (value: TargetMarket) => void;
  onTargetMarketReasonChange: (value: string) => void;
  onRegenerate: () => void;
}

export function ComparisonSetup({
  comparisonRunId,
  targetMarket,
  targetMarketReason,
  locked,
  onComparisonRunIdChange,
  onTargetMarketChange,
  onTargetMarketReasonChange,
  onRegenerate
}: ComparisonSetupProps) {
  const runIdError = validateComparisonRunId(comparisonRunId);

  return (
    <section className="comparison-panel" aria-labelledby="comparison-setup-title">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">1. 비교 조건</p>
          <h2 id="comparison-setup-title">비교 실행 조건</h2>
          <p>target market은 자동 선택되지 않으며 사용자가 직접 고정합니다.</p>
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

        <fieldset className="market-fieldset" disabled={locked}>
          <legend>
            targetMarket <span aria-hidden="true">*</span>
          </legend>
          <div className="market-options">
            {(["JKM", "TTF", "HH"] as const).map((market) => (
              <label key={market}>
                <input
                  type="radio"
                  name="target-market"
                  value={market}
                  checked={targetMarket === market}
                  onChange={() => onTargetMarketChange(market)}
                />
                {market}
              </label>
            ))}
          </div>
          {!targetMarket && (
            <span className="field-help">
              비교 실행 전 JKM, TTF, HH 중 하나를 반드시 선택하세요.
            </span>
          )}
        </fieldset>

        <label className="field comparison-reason-field">
          target market 선택 사유
          <textarea
            value={targetMarketReason}
            disabled={locked}
            placeholder="Event 영향 정보 등을 근거로 선택 사유를 기록하세요."
            onChange={(event) =>
              onTargetMarketReasonChange(event.currentTarget.value)
            }
          />
        </label>
      </div>
    </section>
  );
}
