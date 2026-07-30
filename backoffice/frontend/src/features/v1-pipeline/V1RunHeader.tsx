import { Download, RotateCcw } from "lucide-react";
import type { V1RunState } from "./types";

interface V1RunHeaderProps {
  run: V1RunState;
  onNewRun: () => void;
  onExport: () => void;
  running?: boolean;
}

function formatElapsed(milliseconds: number): string {
  if (milliseconds < 1_000) return `${milliseconds}ms`;
  return `${(milliseconds / 1_000).toFixed(1)}s`;
}

export function V1RunHeader({
  run,
  onNewRun,
  onExport,
  running = false
}: V1RunHeaderProps) {
  const elapsed = Object.values(run.steps).reduce(
    (total, step) => total + (step.elapsedMs ?? 0),
    0
  );
  const tokens = Object.values(run.steps).reduce(
    (total, step) => total + (step.tokenUsage ?? 0),
    0
  );
  const current = run.steps[run.currentStep];

  return (
    <header className="v1-run-header">
      <div>
        <p className="eyebrow">V1 Run · {run.runId.slice(0, 8)}</p>
        <h2>
          {run.event
            ? `#${run.event.miEventId} · ${
                run.event.title || run.event.eventTitle || "제목 없음"
              }`
            : "Event를 선택해 실행을 준비하세요"}
        </h2>
        <p>
          Group {run.scenarioGroupId ? `#${run.scenarioGroupId}` : "—"} ·{" "}
          {run.scenarioGroup
            ? `${run.scenarioGroup.status}/${run.scenarioGroup.stage}`
            : "status/stage —"}
        </p>
      </div>
      <dl className="run-metrics">
        <div>
          <dt>현재 단계</dt>
          <dd>{run.currentStep}</dd>
        </div>
        <div>
          <dt>Run 상태</dt>
          <dd>{current.status}</dd>
        </div>
        <div>
          <dt>Elapsed</dt>
          <dd>{formatElapsed(elapsed)}</dd>
        </div>
        <div>
          <dt>Tokens</dt>
          <dd>{tokens.toLocaleString()}</dd>
        </div>
      </dl>
      <div className="run-actions">
        <button
          className="button secondary"
          type="button"
          disabled={running}
          onClick={onNewRun}
        >
          <RotateCcw aria-hidden="true" size={17} />
          새 실행
        </button>
        <button
          className="button primary"
          type="button"
          disabled={!run.event || running}
          onClick={onExport}
        >
          <Download aria-hidden="true" size={17} />
          결과 Export
        </button>
      </div>
    </header>
  );
}
