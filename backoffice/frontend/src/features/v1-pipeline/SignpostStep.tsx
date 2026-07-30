import { AlertTriangle, LoaderCircle } from "lucide-react";
import type {
  CallbackBody,
  ScenarioTable,
  TableSyncRequest
} from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import type { StepState } from "./types";

interface SignpostStepProps {
  request: TableSyncRequest;
  step: StepState;
  table?: ScenarioTable;
  onExecute: () => void;
  onCancel: () => void;
}

export function SignpostStep({
  request,
  step,
  table,
  onExecute,
  onCancel
}: SignpostStepProps) {
  const body = step.response as CallbackBody | undefined;
  const canRun = ["ready", "error"].includes(step.status);
  const signpostCount =
    table?.rows.reduce(
      (total, row) => total + (row.signposts?.length ?? 0),
      0
    ) ?? 0;

  function execute() {
    if (
      step.status === "error" &&
      !window.confirm(
        "Signpost POST를 다시 실행하면 중복 데이터가 생길 수 있습니다. 명시적으로 재실행할까요?"
      )
    ) {
      return;
    }
    onExecute();
  }

  return (
    <section className="pipeline-step" aria-labelledby="signpost-step-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 3</p>
          <h2 id="signpost-step-title">Signpost</h2>
        </div>
        <span className={`status-badge status-${step.status}`}>
          {step.status}
        </span>
      </div>
      <JsonViewer value={request} label="Signpost request preview" />
      <button
        className="button primary"
        type="button"
        disabled={!canRun || step.status === "running"}
        onClick={execute}
      >
        {step.status === "running" && (
          <LoaderCircle aria-hidden="true" className="spin" size={17} />
        )}
        Signpost 실행
      </button>
      {step.status === "running" && (
        <button className="button secondary" type="button" onClick={onCancel}>
          실행 취소
        </button>
      )}

      {body?.scenarioGroup && (
        <p className="helper-text">
          {body.scenarioGroup.status}/{body.scenarioGroup.stage} · Signpost{" "}
          {signpostCount}건
        </p>
      )}
      {table?.rows.map((row) => (
        <details
          className="signpost-accordion"
          key={row.scenarioId ?? row.displayOrder}
        >
          <summary>
            {row.displayOrder}. {row.title} · {row.signposts?.length ?? 0}건
          </summary>
          {row.signposts?.length ? (
            <div className="signpost-grid">
              {row.signposts.map((signpost, index) => (
                <article key={signpost.signpostId ?? index}>
                  <strong>{signpost.label || "라벨 없음"}</strong>
                  <dl>
                    <div>
                      <dt>Direction</dt>
                      <dd>{signpost.probabilityDirectionCode ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Impact</dt>
                      <dd>{signpost.probabilityImpactScore ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Strength</dt>
                      <dd>{signpost.strength ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Evidence reason</dt>
                      <dd>{signpost.signpostReason ?? "—"}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          ) : (
            <p>생성된 Signpost가 없습니다.</p>
          )}
        </details>
      ))}
      {step.error && (
        <div
          className={`callout ${step.status === "unknown" ? "unknown" : "error"}`}
          role="alert"
        >
          <AlertTriangle aria-hidden="true" size={18} />
          <span>
            {step.error}
            {step.status === "unknown" &&
              " 서버에서 작업이 완료되었을 수 있습니다. 동일 요청을 자동 재시도하지 않습니다."}
          </span>
        </div>
      )}
    </section>
  );
}
