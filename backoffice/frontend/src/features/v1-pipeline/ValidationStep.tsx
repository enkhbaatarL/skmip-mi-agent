import { AlertTriangle, LoaderCircle } from "lucide-react";
import type { CallbackBody, TableSyncRequest } from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import type { StepState } from "./types";

interface ValidationStepProps {
  request: TableSyncRequest;
  step: StepState;
  onExecute: () => void;
  onCancel: () => void;
  onAcknowledge: () => void;
}

export function ValidationStep({
  request,
  step,
  onExecute,
  onCancel,
  onAcknowledge
}: ValidationStepProps) {
  const body = step.response as CallbackBody | undefined;
  const canRun = ["ready", "success", "warning", "error"].includes(step.status);

  function execute() {
    if (
      step.response !== undefined &&
      !window.confirm(
        "Validation을 다시 실행하면 새 응답이 현재 server 기준 table을 대체합니다. 현재 request preview로 재검증할까요?"
      )
    ) {
      return;
    }
    onExecute();
  }

  return (
    <section className="pipeline-step" aria-labelledby="validation-step-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 2</p>
          <h2 id="validation-step-title">Validation</h2>
        </div>
        <span className={`status-badge status-${step.status}`}>
          {step.status}
        </span>
      </div>
      <JsonViewer value={request} label="Validation request preview" />
      <button
        className="button primary"
        type="button"
        disabled={!canRun || step.status === "running"}
        onClick={execute}
      >
        {step.status === "running" && (
          <LoaderCircle aria-hidden="true" className="spin" size={17} />
        )}
        Validation 실행
      </button>
      {step.status === "running" && (
        <button className="button secondary" type="button" onClick={onCancel}>
          실행 취소
        </button>
      )}
      {body && (
        <dl className="result-summary">
          <div>
            <dt>isValid</dt>
            <dd>{String(body.isValid ?? "—")}</dd>
          </div>
          <div>
            <dt>Stage</dt>
            <dd>{body.scenarioGroup?.stage ?? "—"}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{body.reason ?? "—"}</dd>
          </div>
        </dl>
      )}
      {step.status === "warning" && (
        <div className="callout warning" role="status">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>
            {step.warning ?? body?.reason ?? "Validation 결과를 확인하세요."}
          </span>
          {!step.warningAcknowledged && (
            <button
              className="button secondary compact"
              type="button"
              onClick={onAcknowledge}
            >
              확인하고 계속
            </button>
          )}
        </div>
      )}
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
