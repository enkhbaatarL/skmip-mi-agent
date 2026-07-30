import { AlertTriangle, LoaderCircle, Trash2 } from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent
} from "react";
import type {
  CallbackBody,
  CreateScenariosRequest,
  EventDetail,
  SoftDeleteResponse
} from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import type { StepState } from "./types";

interface CreateStepProps {
  event: EventDetail;
  request: CreateScenariosRequest;
  step: StepState;
  duplicateGroup: boolean;
  onExecute: () => void;
  onCancel: () => void;
  onSoftDelete: (token?: string) => Promise<SoftDeleteResponse | undefined>;
}

export function CreateStep({
  event,
  request,
  step,
  duplicateGroup,
  onExecute,
  onCancel,
  onSoftDelete
}: CreateStepProps) {
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [adminToken, setAdminToken] = useState("");
  const [cleanupRunning, setCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<SoftDeleteResponse>();
  const cleanupTriggerRef = useRef<HTMLButtonElement>(null);
  const tokenInputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const body = step.response as CallbackBody | undefined;
  const unknown = step.status === "unknown";

  useEffect(() => {
    if (cleanupOpen) tokenInputRef.current?.focus();
  }, [cleanupOpen]);

  function closeCleanup() {
    setAdminToken("");
    setCleanupOpen(false);
    window.setTimeout(() => cleanupTriggerRef.current?.focus());
  }

  function handleDialogKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape" && !cleanupRunning) {
      event.preventDefault();
      closeCleanup();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled])'
      ) ?? []
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }

  async function cleanup() {
    setCleanupRunning(true);
    const result = await onSoftDelete(adminToken || undefined);
    setCleanupRunning(false);
    if (result) {
      setCleanupResult(result);
      closeCleanup();
    }
  }

  return (
    <section className="pipeline-step" aria-labelledby="create-step-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Step 1</p>
          <h2 id="create-step-title">Create</h2>
        </div>
        <span className={`status-badge status-${step.status}`}>
          {step.status}
        </span>
      </div>

      <p>
        #{event.miEventId} · {event.title || event.eventTitle || "제목 없음"}
      </p>
      {event.relatedScenarioGroup && (
        <div className="callout warning">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>
            기존 Group #{event.relatedScenarioGroup.scenarioGroupId} ·{" "}
            {event.relatedScenarioGroup.status}/
            {event.relatedScenarioGroup.stage}
          </span>
        </div>
      )}
      <JsonViewer value={request} label="Create request preview" />

      <button
        className="button primary"
        type="button"
        disabled={step.status !== "ready"}
        onClick={onExecute}
      >
        {step.status === "running" && (
          <LoaderCircle aria-hidden="true" className="spin" size={17} />
        )}
        Create 실행
      </button>
      {step.status === "running" && (
        <button className="button secondary" type="button" onClick={onCancel}>
          실행 취소
        </button>
      )}
      {step.status !== "ready" && step.status !== "running" && (
        <p className="helper-text">
          Create POST는 이 run에서 다시 전송하지 않습니다. 다시 시도하려면 새
          실행을 시작하세요.
        </p>
      )}

      {body?.scenarioGroup && (
        <dl className="result-summary">
          <div>
            <dt>Scenario Group ID</dt>
            <dd>{body.scenarioGroup.scenarioGroupId}</dd>
          </div>
          <div>
            <dt>Status / Stage</dt>
            <dd>
              {body.scenarioGroup.status} / {body.scenarioGroup.stage}
            </dd>
          </div>
          <div>
            <dt>Scenario</dt>
            <dd>{body.table?.rows.length ?? body.scenarioGroup.scenarioCount ?? 0}</dd>
          </div>
          <div>
            <dt>Dimensions</dt>
            <dd>{body.table?.headers.length ?? 0}</dd>
          </div>
          <div>
            <dt>Elapsed</dt>
            <dd>{step.elapsedMs ?? 0}ms</dd>
          </div>
          <div>
            <dt>Tokens</dt>
            <dd>{step.tokenUsage ?? 0}</dd>
          </div>
        </dl>
      )}

      {step.error && (
        <div className={`callout ${unknown ? "unknown" : "error"}`} role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>
            {step.error}
            {unknown &&
              " 서버에서 작업이 완료되었을 수 있습니다. 동일 요청을 자동 재시도하지 않습니다."}
          </span>
        </div>
      )}

      {duplicateGroup && event.relatedScenarioGroup && (
        <div className="duplicate-cleanup">
          <p>
            Create 실패 reason과 Event의 기존 Group 정보를 확인했습니다. 정리는
            사용자가 명시적으로 실행할 때만 soft delete로 수행됩니다.
          </p>
          <button
            ref={cleanupTriggerRef}
            className="button secondary"
            type="button"
            onClick={() => setCleanupOpen(true)}
          >
            <Trash2 aria-hidden="true" size={16} />
            기존 Group 정리
          </button>
        </div>
      )}

      {cleanupResult && (
        <div className="callout success" role="status">
          Group {cleanupResult.scenarioGroupDeleted}, Scenario{" "}
          {cleanupResult.scenarioDeleted}, Signpost{" "}
          {cleanupResult.signpostDeleted}건을 soft delete했습니다. 새 실행에서 Create를
          진행하세요.
        </div>
      )}

      {cleanupOpen && (
        <div className="modal-backdrop">
          <section
            ref={dialogRef}
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cleanup-dialog-title"
            onKeyDown={handleDialogKeyDown}
          >
            <h3 id="cleanup-dialog-title">기존 Scenario Group 정리 확인</h3>
            <p>
              Group #{event.relatedScenarioGroup?.scenarioGroupId}와 하위 데이터를 soft
              delete합니다. 이 작업은 자동으로 실행되지 않습니다.
            </p>
            <label className="field">
              Admin token (선택, 메모리에만 유지)
              <input
                ref={tokenInputRef}
                type="password"
                autoComplete="off"
                value={adminToken}
                disabled={cleanupRunning}
                onChange={(input) => setAdminToken(input.currentTarget.value)}
              />
            </label>
            <div className="dialog-actions">
              <button
                className="button quiet"
                type="button"
                disabled={cleanupRunning}
                onClick={closeCleanup}
              >
                취소
              </button>
              <button
                className="button primary"
                type="button"
                disabled={cleanupRunning}
                onClick={() => void cleanup()}
              >
                {cleanupRunning ? "정리 중" : "정리 확인 실행"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
