import { CheckCircle2, Clipboard, LockKeyhole } from "lucide-react";
import type { EventDetail } from "../../domain/apiTypes";
import type { RuntimeSnapshot } from "../../domain/runtime";

interface ManifestSummaryProps {
  runtime: RuntimeSnapshot;
  selectedEvents: EventDetail[];
  comparisonRunId: string;
  locked: boolean;
  canExecute: boolean;
  onExecute: () => void;
}

export function ManifestSummary({
  runtime,
  selectedEvents,
  comparisonRunId,
  locked,
  canExecute,
  onExecute
}: ManifestSummaryProps) {
  return (
    <section className="comparison-panel manifest-panel" aria-labelledby="manifest-title">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">Manifest</p>
          <h2 id="manifest-title">실행 조건 확인</h2>
          <p>비교 실행을 누르면 아래 값과 Event 순서가 고정됩니다.</p>
        </div>
        {locked && (
          <span className="status-badge status-ready">
            <LockKeyhole aria-hidden="true" size={15} />
            잠김
          </span>
        )}
      </div>

      <dl className="manifest-grid">
        <div>
          <dt>Base URL</dt>
          <dd>{runtime.agentBaseUrl}</dd>
        </div>
        <div>
          <dt>userId</dt>
          <dd>{runtime.userId}</dd>
        </div>
        <div>
          <dt>Timeout</dt>
          <dd>{runtime.timeoutMs.toLocaleString()} ms</dd>
        </div>
        <div className="manifest-wide">
          <dt>comparisonRunId</dt>
          <dd className="copy-value">
            <code>{comparisonRunId || "입력 필요"}</code>
            <button
              className="icon-button"
              type="button"
              aria-label="comparisonRunId 복사"
              disabled={!comparisonRunId}
              onClick={() => void navigator.clipboard.writeText(comparisonRunId)}
            >
              <Clipboard aria-hidden="true" size={16} />
            </button>
          </dd>
        </div>
      </dl>

      <div className="manifest-events">
        <h3>Ordered Events · {selectedEvents.length}건</h3>
        {selectedEvents.length === 0 ? (
          <p className="empty-hint">중복 없는 Event 2~5건을 선택하세요.</p>
        ) : (
          <ol>
            {selectedEvents.map((event) => (
              <li key={event.miEventId}>
                <span>
                  #{event.miEventId} · {event.title || event.eventTitle}
                </span>
                <span className="detail-success">
                  <CheckCircle2 aria-hidden="true" size={15} />
                  상세 조회 성공
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="manifest-actions">
        <p>
          {!canExecute && !locked
            ? "Event 2~5건과 유효한 comparisonRunId가 필요합니다."
            : "각 version POST는 이 실행에서 정확히 한 번만 전송됩니다."}
        </p>
        <button
          className="button primary"
          type="button"
          disabled={!canExecute || locked}
          onClick={onExecute}
        >
          <LockKeyhole aria-hidden="true" size={17} />
          비교 실행
        </button>
      </div>
    </section>
  );
}
