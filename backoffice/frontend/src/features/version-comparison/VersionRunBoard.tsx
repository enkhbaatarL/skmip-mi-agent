import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  CircleHelp,
  LoaderCircle,
  OctagonX,
  Square
} from "lucide-react";
import type { ApiVersion } from "../../domain/apiTypes";
import {
  summarizeChecks,
  type DeterministicCheckResult
} from "../../domain/deterministicChecks";
import type { RunStatus } from "../../domain/judgments";
import { totalTokens } from "../../domain/tokenUsage";
import {
  VERSION_ORDER,
  type VersionRunState
} from "./types";

const STATUS_PRESENTATION: Record<
  RunStatus,
  { label: string; icon: typeof Circle }
> = {
  idle: { label: "대기", icon: Circle },
  ready: { label: "준비", icon: Circle },
  running: { label: "실행 중", icon: LoaderCircle },
  success: { label: "성공", icon: CheckCircle2 },
  warning: { label: "경고", icon: AlertTriangle },
  error: { label: "실패", icon: OctagonX },
  unknown: { label: "결과 불명", icon: CircleHelp }
};

interface VersionRunBoardProps {
  versions: Record<ApiVersion, VersionRunState>;
  v4Waiting: boolean;
  checks?: Record<ApiVersion, DeterministicCheckResult[]>;
  onCancel?: (version: ApiVersion) => void;
}

function formatTime(value: string | undefined): string {
  return value ? new Date(value).toLocaleTimeString() : "—";
}

function errorSummary(state: VersionRunState): string | undefined {
  if (state.integrityIssues.length > 0) return state.integrityIssues.join(" · ");
  if (state.error) return state.error;
  if (state.response?.status === "error") return state.response.message;
  if (state.status === "unknown") {
    return "서버에서 작업이 완료되었을 수 있습니다. 자동 재시도하지 않습니다.";
  }
  return undefined;
}

export function VersionRunBoard({
  versions,
  v4Waiting,
  checks,
  onCancel
}: VersionRunBoardProps) {
  return (
    <section className="comparison-panel" aria-labelledby="version-board-title">
      <div className="section-heading compact-heading">
        <div>
          <p className="eyebrow">2. 실행</p>
          <h2 id="version-board-title">Version 실행 상태</h2>
          <p>v2/v3 병렬 실행이 모두 종료된 뒤 v4가 시작됩니다.</p>
        </div>
      </div>

      <div className="version-board" tabIndex={0}>
        {VERSION_ORDER.map((version) => {
          const state = versions[version];
          const presentation = STATUS_PRESENTATION[state.status];
          const StatusIcon = presentation.icon;
          const summary = errorSummary(state);
          const checkSummary = summarizeChecks(checks?.[version] ?? []);
          const data = state.response?.data;
          const waiting = version === "v4" && v4Waiting && state.status === "ready";
          return (
            <article
              className={`version-card version-${state.status}`}
              key={version}
              aria-busy={state.status === "running"}
            >
              <header>
                <div>
                  <strong>{version}</strong>
                  <small>{state.generationStrategy}</small>
                </div>
                <span
                  className={`status-badge status-${waiting ? "ready" : state.status}`}
                  role="status"
                  aria-live="polite"
                >
                  <StatusIcon
                    aria-hidden="true"
                    size={16}
                    className={state.status === "running" ? "spin" : undefined}
                  />
                  {waiting ? "v2/v3 종료 대기" : presentation.label}
                </span>
              </header>

              <dl className="version-metrics">
                <div>
                  <dt>시작</dt>
                  <dd>{formatTime(state.startedAt)}</dd>
                </div>
                <div>
                  <dt>종료</dt>
                  <dd>{formatTime(state.finishedAt)}</dd>
                </div>
                <div>
                  <dt>Elapsed</dt>
                  <dd>
                    {state.elapsedMs === undefined
                      ? "—"
                      : `${state.elapsedMs.toLocaleString()} ms`}
                  </dd>
                </div>
                <div>
                  <dt>HTTP</dt>
                  <dd>{state.call?.httpStatus ?? "—"}</dd>
                </div>
                <div>
                  <dt>Scenario Group</dt>
                  <dd>
                    {data?.scenarioGroup.scenarioGroupId
                      ? `#${data.scenarioGroup.scenarioGroupId}`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Token</dt>
                  <dd>{totalTokens(data?.usage) ?? "—"}</dd>
                </div>
                <div>
                  <dt>Checks</dt>
                  <dd>
                    P {checkSummary.pass} · W {checkSummary.warn} · F{" "}
                    {checkSummary.fail}
                  </dd>
                </div>
              </dl>

              {summary && (
                <p className={`version-error ${state.status}`} role="alert">
                  {summary}
                </p>
              )}
              {state.status === "running" && onCancel && (
                <button
                  className="button quiet compact"
                  type="button"
                  onClick={() => onCancel(version)}
                >
                  <Square aria-hidden="true" size={14} />
                  {version} 요청 취소
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
