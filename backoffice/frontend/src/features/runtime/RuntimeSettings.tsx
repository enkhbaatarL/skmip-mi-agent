import { useState, type FormEvent } from "react";
import { LoaderCircle, RotateCcw, Save, Wifi } from "lucide-react";
import {
  validateRuntimeConfig,
  type RuntimeConfig,
  type RuntimeField,
  type RuntimeValidationErrors
} from "../../domain/runtime";

interface RuntimeSettingsProps {
  config: RuntimeConfig;
  disabled?: boolean;
  checking: boolean;
  connectionStatus?: "unchecked" | "checking" | "connected" | "failed";
  connectionMessage?: string;
  onChange: (config: RuntimeConfig) => void;
  onCheckConnection: () => Promise<void>;
  onSave: () => void;
  onReset: () => Promise<void>;
}

export function RuntimeSettings({
  config,
  disabled = false,
  checking,
  connectionStatus = "unchecked",
  connectionMessage,
  onChange,
  onCheckConnection,
  onSave,
  onReset
}: RuntimeSettingsProps) {
  const [errors, setErrors] = useState<RuntimeValidationErrors>({});
  const [message, setMessage] = useState("");

  function updateField(field: RuntimeField, value: string) {
    onChange({ ...config, [field]: value });
    setErrors((current) => ({ ...current, [field]: undefined }));
    setMessage("");
  }

  function validate(): boolean {
    const nextErrors = validateRuntimeConfig(config);
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleConnectionCheck(event: FormEvent) {
    event.preventDefault();
    if (!validate()) return;
    setMessage("");
    await onCheckConnection();
  }

  function handleSave() {
    if (!validate()) return;
    onSave();
    setMessage("Runtime 설정을 저장했습니다.");
  }

  async function handleReset() {
    setErrors({});
    setMessage("");
    await onReset();
  }

  return (
    <section
      className="runtime-settings"
      id="runtime-settings"
      aria-labelledby="runtime-settings-title"
      aria-busy={checking}
    >
      <div className="runtime-heading">
        <div>
          <p className="eyebrow">Runtime Settings</p>
          <h2 id="runtime-settings-title">Agent 연결 설정</h2>
        </div>
        <p className="runtime-help">
          브라우저에서 Agent sync API를 직접 호출합니다.
        </p>
      </div>

      <form className="runtime-form" onSubmit={handleConnectionCheck} noValidate>
        <div className="field field-base-url">
          <label htmlFor="agent-base-url">Agent Base URL</label>
          <input
            id="agent-base-url"
            name="agentBaseUrl"
            type="url"
            value={config.agentBaseUrl}
            disabled={disabled || checking}
            aria-invalid={Boolean(errors.agentBaseUrl)}
            aria-describedby={
              errors.agentBaseUrl ? "agent-base-url-error" : undefined
            }
            onChange={(event) =>
              updateField("agentBaseUrl", event.currentTarget.value)
            }
          />
          {errors.agentBaseUrl && (
            <span className="field-error" id="agent-base-url-error">
              {errors.agentBaseUrl}
            </span>
          )}
        </div>

        <div className="field">
          <label htmlFor="runtime-user-id">userId</label>
          <input
            id="runtime-user-id"
            name="userId"
            inputMode="numeric"
            value={config.userId}
            disabled={disabled || checking}
            aria-invalid={Boolean(errors.userId)}
            aria-describedby={errors.userId ? "runtime-user-id-error" : undefined}
            onChange={(event) => updateField("userId", event.currentTarget.value)}
          />
          {errors.userId && (
            <span className="field-error" id="runtime-user-id-error">
              {errors.userId}
            </span>
          )}
        </div>

        <div className="field">
          <label htmlFor="runtime-timeout">Timeout (seconds)</label>
          <input
            id="runtime-timeout"
            name="timeoutSeconds"
            type="number"
            min="1"
            step="1"
            value={config.timeoutSeconds}
            disabled={disabled || checking}
            aria-invalid={Boolean(errors.timeoutSeconds)}
            aria-describedby={
              errors.timeoutSeconds ? "runtime-timeout-error" : undefined
            }
            onChange={(event) =>
              updateField("timeoutSeconds", event.currentTarget.value)
            }
          />
          {errors.timeoutSeconds && (
            <span className="field-error" id="runtime-timeout-error">
              {errors.timeoutSeconds}
            </span>
          )}
        </div>

        <div className="field">
          <label htmlFor="runtime-authorization">
            Authorization (memory only)
          </label>
          <input
            id="runtime-authorization"
            name="authorization"
            type="password"
            autoComplete="off"
            value={config.authorization ?? ""}
            disabled={disabled || checking}
            onChange={(event) =>
              updateField("authorization", event.currentTarget.value)
            }
          />
          <small>저장·Evidence·Export에는 인증 원문을 남기지 않습니다.</small>
        </div>

        <div className="runtime-actions">
          <button
            className="button primary"
            type="submit"
            disabled={disabled || checking}
          >
            {checking ? (
              <LoaderCircle aria-hidden="true" className="spin" size={17} />
            ) : (
              <Wifi aria-hidden="true" size={17} />
            )}
            {checking ? "확인 중" : "연결 확인"}
          </button>
          <button
            className="button secondary"
            type="button"
            disabled={disabled || checking}
            onClick={handleSave}
          >
            <Save aria-hidden="true" size={17} />
            저장
          </button>
          <button
            className="button quiet"
            type="button"
            disabled={disabled || checking}
            onClick={() => void handleReset()}
          >
            <RotateCcw aria-hidden="true" size={17} />
            초기화
          </button>
        </div>
      </form>
      {connectionMessage && (
        <div
          className={`callout ${
            connectionStatus === "failed" ? "error" : "success"
          }`}
          role={connectionStatus === "failed" ? "alert" : "status"}
        >
          {connectionMessage}
        </div>
      )}
      <span className="sr-only" aria-live="polite">
        {checking ? "Agent 연결을 확인하고 있습니다." : message}
      </span>
    </section>
  );
}
