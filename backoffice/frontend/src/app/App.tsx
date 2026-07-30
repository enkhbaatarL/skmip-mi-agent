import { useCallback, useEffect, useRef, useState } from "react";
import { createAgentClient } from "../api/agentClient";
import type { ApiCallRecord } from "../domain/apiCall";
import {
  connectionFailureGuidance,
  isMixedContentRequest,
  MIXED_CONTENT_GUIDANCE
} from "../domain/connection";
import {
  DEFAULT_RUNTIME_CONFIG,
  createRuntimeSnapshot,
  type RuntimeConfig
} from "../domain/runtime";
import {
  clearRuntimeConfig,
  loadRuntimeConfig,
  resolveRuntimeConfig,
  saveRuntimeConfig
} from "../features/runtime/runtimeStorage";
import type { V1ClientContext } from "../features/v1-pipeline/V1Workspace";
import type { ComparisonClientContext } from "../features/version-comparison/ComparisonWorkspace";
import {
  AppShell,
  type ConnectionStatus
} from "./AppShell";

export function App() {
  const [runtimeConfig, setRuntimeConfig] =
    useState<RuntimeConfig>(loadRuntimeConfig);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("unchecked");
  const [connectionMessage, setConnectionMessage] = useState("");
  const [calls, setCalls] = useState<ApiCallRecord[]>([]);
  const [v1RunLocked, setV1RunLocked] = useState(false);
  const [comparisonRunLocked, setComparisonRunLocked] = useState(false);
  const userEditedRuntime = useRef(false);

  const appendCall = useCallback((record: ApiCallRecord) => {
    setCalls((current) => [...current, record]);
  }, []);

  const createV1Client = useCallback((): V1ClientContext => {
    const runtime = createRuntimeSnapshot(runtimeConfig);
    return {
      runtime,
      client: createAgentClient(runtime, appendCall, { workflow: "v1" })
    };
  }, [appendCall, runtimeConfig]);

  const createComparisonClient = useCallback((): ComparisonClientContext => {
    const runtime = createRuntimeSnapshot(runtimeConfig);
    return {
      runtime,
      client: createAgentClient(runtime, appendCall, {
        workflow: "comparison"
      })
    };
  }, [appendCall, runtimeConfig]);

  useEffect(() => {
    let active = true;
    void resolveRuntimeConfig().then((resolved) => {
      if (active && !userEditedRuntime.current) setRuntimeConfig(resolved);
    });
    return () => {
      active = false;
    };
  }, []);

  function handleRuntimeChange(config: RuntimeConfig) {
    userEditedRuntime.current = true;
    setRuntimeConfig(config);
    setConnectionStatus("unchecked");
    setConnectionMessage("");
  }

  async function handleConnectionCheck() {
    const snapshot = createRuntimeSnapshot(runtimeConfig);
    if (
      isMixedContentRequest(
        snapshot.agentBaseUrl,
        window.location.protocol
      )
    ) {
      setConnectionStatus("failed");
      setConnectionMessage(MIXED_CONTENT_GUIDANCE);
      return;
    }
    setConnectionStatus("checking");
    setConnectionMessage("");
    const client = createAgentClient(snapshot, appendCall, {
      workflow: "runtime"
    });
    const result = await client.checkConnection();
    const connected =
      result.ok && result.record.judgment === "success";
    setConnectionStatus(connected ? "connected" : "failed");
    setConnectionMessage(
      connected
        ? "Agent /events 연결 확인에 성공했습니다."
        : connectionFailureGuidance(result.record)
    );
  }

  function handleSaveRuntime() {
    saveRuntimeConfig(runtimeConfig);
  }

  async function handleResetRuntime() {
    clearRuntimeConfig();
    userEditedRuntime.current = false;
    setConnectionStatus("unchecked");
    setConnectionMessage("");
    try {
      setRuntimeConfig(await resolveRuntimeConfig());
    } catch {
      setRuntimeConfig({ ...DEFAULT_RUNTIME_CONFIG });
    }
  }

  return (
    <AppShell
      runtimeConfig={runtimeConfig}
      connectionStatus={connectionStatus}
      connectionMessage={connectionMessage}
      calls={calls}
      runtimeLocked={v1RunLocked || comparisonRunLocked}
      createV1Client={createV1Client}
      createComparisonClient={createComparisonClient}
      onV1RunLockChange={setV1RunLocked}
      onComparisonRunLockChange={setComparisonRunLocked}
      onRuntimeChange={handleRuntimeChange}
      onCheckConnection={handleConnectionCheck}
      onSaveRuntime={handleSaveRuntime}
      onResetRuntime={handleResetRuntime}
    />
  );
}
