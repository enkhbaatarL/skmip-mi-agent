export const DEFAULT_TIMEOUT_SECONDS = 1_200;
export const FALLBACK_AGENT_BASE_URL = "http://127.0.0.1:8001";

export interface RuntimeConfig {
  agentBaseUrl: string;
  userId: string;
  timeoutSeconds: string;
  authorization?: string;
}

export type RuntimeSnapshot = Readonly<{
  agentBaseUrl: string;
  userId: number;
  timeoutMs: number;
  authorization?: string;
}>;

export type RuntimeField =
  | "agentBaseUrl"
  | "userId"
  | "timeoutSeconds"
  | "authorization";
export type RuntimeValidationErrors = Partial<Record<RuntimeField, string>>;

export const DEFAULT_RUNTIME_CONFIG: RuntimeConfig = {
  agentBaseUrl: FALLBACK_AGENT_BASE_URL,
  userId: "",
  timeoutSeconds: String(DEFAULT_TIMEOUT_SECONDS)
};

export function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function validateRuntimeConfig(config: RuntimeConfig): RuntimeValidationErrors {
  const errors: RuntimeValidationErrors = {};
  const baseUrl = normalizeBaseUrl(config.agentBaseUrl);

  if (!baseUrl) {
    errors.agentBaseUrl = "Agent Base URL을 입력하세요.";
  } else {
    try {
      const url = new URL(baseUrl);
      if (!["http:", "https:"].includes(url.protocol)) {
        errors.agentBaseUrl = "http 또는 https URL을 입력하세요.";
      }
    } catch {
      errors.agentBaseUrl = "올바른 URL을 입력하세요.";
    }
  }

  const userId = Number(config.userId);
  if (!config.userId.trim()) {
    errors.userId = "userId를 입력하세요.";
  } else if (!Number.isSafeInteger(userId)) {
    errors.userId = "userId는 정수여야 합니다.";
  }

  const timeoutSeconds = Number(config.timeoutSeconds);
  if (!config.timeoutSeconds.trim()) {
    errors.timeoutSeconds = "Timeout을 입력하세요.";
  } else if (!Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0) {
    errors.timeoutSeconds = "Timeout은 0보다 큰 숫자여야 합니다.";
  }

  return errors;
}

export function createRuntimeSnapshot(config: RuntimeConfig): RuntimeSnapshot {
  const errors = validateRuntimeConfig(config);
  if (Object.keys(errors).length > 0) {
    throw new Error("Runtime 설정이 올바르지 않습니다.");
  }

  return Object.freeze({
    agentBaseUrl: normalizeBaseUrl(config.agentBaseUrl),
    userId: Number(config.userId),
    timeoutMs: Number(config.timeoutSeconds) * 1_000,
    ...(config.authorization?.trim()
      ? { authorization: config.authorization.trim() }
      : {})
  });
}
