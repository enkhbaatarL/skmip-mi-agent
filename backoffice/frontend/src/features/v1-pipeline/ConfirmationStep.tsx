import { AlertTriangle, LoaderCircle } from "lucide-react";
import type {
  ConfirmationRequest,
  ScenarioGroupDetailResponse,
  WrapperBody,
  ConfirmationData
} from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import type { StepState } from "./types";

interface ConfirmationStepProps {
  request?: ConfirmationRequest;
  latestDetail?: ScenarioGroupDetailResponse;
  step: StepState;
  onPrepare: () => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationStep({
  request,
  latestDetail,
  step,
  onPrepare,
  onConfirm,
  onCancel
}: ConfirmationStepProps) {
  const body = step.response as WrapperBody<ConfirmationData> | undefined;
  const prepared = Boolean(request && latestDetail);
  const canRun = ["ready", "error"].includes(step.status);

  function prepare() {
    if (
      step.status === "error" &&
      !window.confirm(
        "Confirmation 단계를 다시 준비합니다. 최신 detail을 다시 조회할까요?"
      )
    ) {
      return;
    }
    onPrepare();
  }

  function confirm() {
    if (
      step.status === "error" &&
      !window.confirm(
        "Confirmation POST를 다시 실행하면 중복 처리될 수 있습니다. 명시적으로 재실행할까요?"
      )
    ) {
      return;
    }
    onConfirm();
  }

  return (
    <section className="pipeline-step" aria-labelledby="confirmation-step-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 4</p>
          <h2 id="confirmation-step-title">Confirmation</h2>
        </div>
        <span className={`status-badge status-${step.status}`}>
          {step.status}
        </span>
      </div>
      <p className="helper-text">
        먼저 최신 Group detail을 GET해 request preview를 구성합니다. 내용을
        검토한 뒤 별도 승인 버튼으로 Confirmation POST를 실행합니다.
      </p>
      {latestDetail && (
        <>
          <div className="final-detail-summary">
            <h3>{latestDetail.scenarioGroup.title}</h3>
            <p>{latestDetail.scenarioGroup.description ?? "설명 없음"}</p>
            <span>
              Scenario {latestDetail.scenarioCount} · Signpost{" "}
              {latestDetail.signpostCount}
            </span>
          </div>
          <div
            className="table-scroll final-table-scroll"
            tabIndex={0}
            aria-label="최신 Scenario Group 최종 table"
          >
            <table className="event-table">
              <thead>
                <tr>
                  <th scope="col">순서</th>
                  <th scope="col">Title</th>
                  {latestDetail.table.headers.map((header) => (
                    <th scope="col" key={header.key}>
                      {header.label}
                    </th>
                  ))}
                  <th scope="col">Signpost</th>
                </tr>
              </thead>
              <tbody>
                {latestDetail.table.rows.map((row) => (
                  <tr key={row.scenarioId ?? row.displayOrder}>
                    <td>{row.displayOrder}</td>
                    <td>{row.title}</td>
                    {latestDetail.table.headers.map((header) => (
                      <td key={header.key}>
                        {row.cells[header.key] == null
                          ? "—"
                          : String(row.cells[header.key])}
                      </td>
                    ))}
                    <td>{row.signposts?.length ?? 0}건</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <JsonViewer
        value={
          request ??
          "최신 detail 조회 후 정확한 request preview가 표시됩니다."
        }
        label="Confirmation request preview"
      />
      {!prepared ? (
        <button
          className="button primary"
          type="button"
          disabled={!canRun || step.status === "running"}
          onClick={prepare}
        >
          {step.status === "running" && (
            <LoaderCircle aria-hidden="true" className="spin" size={17} />
          )}
          최신 detail 조회
        </button>
      ) : (
        <button
          className="button primary"
          type="button"
          disabled={!canRun || step.status === "running"}
          onClick={confirm}
        >
          {step.status === "running" && (
            <LoaderCircle aria-hidden="true" className="spin" size={17} />
          )}
          Confirmation 승인 및 실행
        </button>
      )}
      {step.status === "running" && (
        <button className="button secondary" type="button" onClick={onCancel}>
          실행 취소
        </button>
      )}
      {body && (
        <dl className="result-summary">
          <div>
            <dt>Status</dt>
            <dd>{body.status}</dd>
          </div>
          <div>
            <dt>Message</dt>
            <dd>{body.message}</dd>
          </div>
          <div>
            <dt>Final stage</dt>
            <dd>{body.data?.stage ?? "—"}</dd>
          </div>
        </dl>
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
