import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  CircleHelp,
  CircleX,
  LoaderCircle,
  Lock
} from "lucide-react";
import type { RunStatus } from "../../domain/judgments";
import type { V1StepId, V1RunState } from "./types";

interface StepRailProps {
  run: V1RunState;
  onAcknowledgeWarning: () => void;
}

const steps: Array<{ id: V1StepId; label: string }> = [
  { id: "create", label: "Create" },
  { id: "validation", label: "Validation" },
  { id: "signpost", label: "Signpost" },
  { id: "confirmation", label: "Confirmation" }
];

const statusPresentation = {
  idle: { label: "대기", icon: Circle },
  ready: { label: "준비", icon: Circle },
  running: { label: "실행 중", icon: LoaderCircle },
  success: { label: "성공", icon: CheckCircle2 },
  warning: { label: "경고", icon: AlertTriangle },
  error: { label: "실패", icon: CircleX },
  unknown: { label: "결과 불명", icon: CircleHelp }
} satisfies Record<RunStatus, { label: string; icon: typeof Circle }>;

export function StepRail({
  run,
  onAcknowledgeWarning
}: StepRailProps) {
  const blockingIndex = steps.findIndex(({ id }) =>
    ["error", "unknown"].includes(run.steps[id].status)
  );

  return (
    <ol className="step-rail" aria-label="v1 pipeline 단계">
      {steps.map((step, index) => {
        const state = run.steps[step.id];
        const presentation = statusPresentation[state.status];
        const StatusIcon = presentation.icon;
        const locked =
          index > 0 &&
          (index > steps.findIndex(({ id }) => id === run.currentStep) ||
            (blockingIndex >= 0 && index > blockingIndex));
        return (
          <li
            key={step.id}
            className={`step-chip status-${state.status} ${
              run.currentStep === step.id ? "active" : ""
            }`}
            aria-current={run.currentStep === step.id ? "step" : undefined}
          >
            <span className="step-number">{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <span className="step-status">
                {locked ? (
                  <Lock aria-hidden="true" size={15} />
                ) : (
                  <StatusIcon
                    aria-hidden="true"
                    size={15}
                    className={state.status === "running" ? "spin" : undefined}
                  />
                )}
                {locked ? "잠김" : presentation.label}
              </span>
              {state.summary && <small>{state.summary}</small>}
              {locked && blockingIndex >= 0 && (
                <small>
                  {steps[blockingIndex].label} 결과가{" "}
                  {run.steps[steps[blockingIndex].id].status} 상태입니다.
                </small>
              )}
              {step.id === "validation" &&
                state.status === "warning" &&
                !state.warningAcknowledged && (
                  <button
                    className="button quiet compact"
                    type="button"
                    onClick={onAcknowledgeWarning}
                  >
                    확인하고 계속
                  </button>
                )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
