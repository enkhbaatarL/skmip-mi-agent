import {
  DEFAULT_RUNTIME_CONFIG,
  FALLBACK_AGENT_BASE_URL,
  normalizeBaseUrl,
  type RuntimeConfig
} from "../../domain/runtime";

export const RUNTIME_STORAGE_KEY = "scenario-comparison.runtime";

export type StoredRuntimeConfig = Pick<
  RuntimeConfig,
  "agentBaseUrl" | "userId" | "timeoutSeconds"
>;

type RuntimeResolutionOptions = {
  userInput?: Partial<RuntimeConfig>;
  storage?: Storage;
  fetcher?: typeof fetch;
  configUrl?: string;
  buildTimeBaseUrl?: string;
};

function getBrowserStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

export function readStoredRuntimeConfig(
  storage: Storage | undefined = getBrowserStorage()
): StoredRuntimeConfig | null {
  if (!storage) return null;

  try {
    const raw = storage.getItem(RUNTIME_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Record<keyof RuntimeConfig, unknown>>;

    if (
      typeof parsed.agentBaseUrl !== "string" ||
      typeof parsed.userId !== "string" ||
      typeof parsed.timeoutSeconds !== "string"
    ) {
      return null;
    }

    return {
      agentBaseUrl: parsed.agentBaseUrl,
      userId: parsed.userId,
      timeoutSeconds: parsed.timeoutSeconds
    };
  } catch {
    return null;
  }
}

export function loadRuntimeConfig(
  storage: Storage | undefined = getBrowserStorage()
): RuntimeConfig {
  return readStoredRuntimeConfig(storage) ?? { ...DEFAULT_RUNTIME_CONFIG };
}

export function saveRuntimeConfig(
  config: RuntimeConfig,
  storage: Storage | undefined = getBrowserStorage()
): void {
  if (!storage) return;

  const safeConfig: StoredRuntimeConfig = {
    agentBaseUrl: normalizeBaseUrl(config.agentBaseUrl),
    userId: config.userId,
    timeoutSeconds: config.timeoutSeconds
  };
  storage.setItem(RUNTIME_STORAGE_KEY, JSON.stringify(safeConfig));
}

export function clearRuntimeConfig(
  storage: Storage | undefined = getBrowserStorage()
): void {
  storage?.removeItem(RUNTIME_STORAGE_KEY);
}

async function readPublicConfigBaseUrl(
  fetcher: typeof fetch,
  configUrl: string
): Promise<string | undefined> {
  try {
    const response = await fetcher(configUrl, { cache: "no-store" });
    if (!response.ok) return undefined;
    const body = (await response.json()) as { agentBaseUrl?: unknown };
    return typeof body.agentBaseUrl === "string" && body.agentBaseUrl.trim()
      ? body.agentBaseUrl
      : undefined;
  } catch {
    return undefined;
  }
}

function defaultConfigUrl(): string {
  if (typeof document === "undefined") return "config.json";
  return new URL("config.json", document.baseURI).toString();
}

function getBuildTimeBaseUrl(): string | undefined {
  const environment = (
    import.meta as ImportMeta & { env?: Record<string, string | undefined> }
  ).env;
  return environment?.VITE_AGENT_BASE_URL;
}

export async function resolveRuntimeConfig(
  options: RuntimeResolutionOptions = {}
): Promise<RuntimeConfig> {
  const storage = options.storage ?? getBrowserStorage();
  const stored = readStoredRuntimeConfig(storage);
  const userBaseUrl = options.userInput?.agentBaseUrl;
  const publicConfigBaseUrl =
    userBaseUrl?.trim() || stored?.agentBaseUrl.trim()
      ? undefined
      : await readPublicConfigBaseUrl(
          options.fetcher ?? fetch,
          options.configUrl ?? defaultConfigUrl()
        );
  const agentBaseUrl =
    userBaseUrl?.trim() ||
    stored?.agentBaseUrl.trim() ||
    publicConfigBaseUrl?.trim() ||
    options.buildTimeBaseUrl?.trim() ||
    getBuildTimeBaseUrl()?.trim() ||
    FALLBACK_AGENT_BASE_URL;

  return {
    agentBaseUrl: normalizeBaseUrl(agentBaseUrl),
    userId:
      options.userInput?.userId ??
      stored?.userId ??
      DEFAULT_RUNTIME_CONFIG.userId,
    timeoutSeconds:
      options.userInput?.timeoutSeconds ??
      stored?.timeoutSeconds ??
      DEFAULT_RUNTIME_CONFIG.timeoutSeconds,
    ...(options.userInput?.authorization
      ? { authorization: options.userInput.authorization }
      : {})
  };
}
