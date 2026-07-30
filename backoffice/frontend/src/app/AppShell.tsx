import {
  useRef,
  useState,
  type KeyboardEvent
} from "react";
import {
  CheckCircle2,
  CircleOff,
  Database,
  LoaderCircle,
  Settings2,
  XCircle
} from "lucide-react";
import type { ApiCallRecord } from "../domain/apiCall";
import type { RuntimeConfig } from "../domain/runtime";
import { EvidenceDrawer } from "../features/evidence/EvidenceDrawer";
import { RuntimeSettings } from "../features/runtime/RuntimeSettings";
import { V1Workspace } from "../features/v1-pipeline/V1Workspace";
import type { V1ClientContext } from "../features/v1-pipeline/V1Workspace";
import { ComparisonWorkspace } from "../features/version-comparison/ComparisonWorkspace";
import type { ComparisonClientContext } from "../features/version-comparison/ComparisonWorkspace";

export type WorkspaceId = "v1" | "comparison";
export type ConnectionStatus =
  | "unchecked"
  | "checking"
  | "connected"
  | "failed";

interface AppShellProps {
  runtimeConfig: RuntimeConfig;
  connectionStatus: ConnectionStatus;
  connectionMessage?: string;
  calls: ApiCallRecord[];
  runtimeLocked: boolean;
  createV1Client: () => V1ClientContext;
  createComparisonClient: () => ComparisonClientContext;
  onV1RunLockChange: (locked: boolean) => void;
  onComparisonRunLockChange: (locked: boolean) => void;
  onRuntimeChange: (config: RuntimeConfig) => void;
  onCheckConnection: () => Promise<void>;
  onSaveRuntime: () => void;
  onResetRuntime: () => Promise<void>;
}

const workspaces: Array<{ id: WorkspaceId; label: string }> = [
  { id: "v1", label: "v1 단일 이벤트" },
  { id: "comparison", label: "v2/v3/v4 비교" }
];

const connectionPresentation = {
  unchecked: { text: "연결 안 됨", icon: CircleOff },
  checking: { text: "확인 중", icon: LoaderCircle },
  connected: { text: "연결됨", icon: CheckCircle2 },
  failed: { text: "연결 실패", icon: XCircle }
} satisfies Record<
  ConnectionStatus,
  { text: string; icon: typeof CircleOff }
>;

export function AppShell({
  runtimeConfig,
  connectionStatus,
  connectionMessage,
  calls,
  runtimeLocked,
  createV1Client,
  createComparisonClient,
  onV1RunLockChange,
  onComparisonRunLockChange,
  onRuntimeChange,
  onCheckConnection,
  onSaveRuntime,
  onResetRuntime
}: AppShellProps) {
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>("v1");
  const [settingsOpen, setSettingsOpen] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidenceTriggerRef = useRef<HTMLButtonElement>(null);
  const connection = connectionPresentation[connectionStatus];
  const ConnectionIcon = connection.icon;

  function handleWorkspaceKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number
  ) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? workspaces.length - 1
          : (index + (event.key === "ArrowRight" ? 1 : -1) + workspaces.length) %
            workspaces.length;
    const workspace = workspaces[nextIndex];
    setActiveWorkspace(workspace.id);
    document.getElementById(`workspace-tab-${workspace.id}`)?.focus();
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            SC
          </span>
          <div>
            <h1>Scenario Comparison</h1>
            <p>Scenario Group Agent QA</p>
          </div>
        </div>

        <div className="header-actions">
          <span
            className={`connection-badge connection-${connectionStatus}`}
            role="status"
            aria-live="polite"
          >
            <ConnectionIcon
              aria-hidden="true"
              className={connectionStatus === "checking" ? "spin" : undefined}
              size={17}
            />
            {connection.text}
          </span>
          <button
            className="button secondary"
            type="button"
            aria-expanded={settingsOpen}
            aria-controls="runtime-settings"
            onClick={() => setSettingsOpen((current) => !current)}
          >
            <Settings2 aria-hidden="true" size={17} />
            Runtime 설정{runtimeLocked ? " · 실행 중 잠금" : ""}
          </button>
          <button
            ref={evidenceTriggerRef}
            className="button secondary"
            type="button"
            aria-haspopup="dialog"
            onClick={() => setEvidenceOpen(true)}
          >
            <Database aria-hidden="true" size={17} />
            Evidence
            {calls.length > 0 && <span className="count-badge">{calls.length}</span>}
          </button>
        </div>
      </header>

      <main className="page">
        {settingsOpen && (
          <RuntimeSettings
            config={runtimeConfig}
            disabled={runtimeLocked}
            checking={connectionStatus === "checking"}
            connectionStatus={connectionStatus}
            connectionMessage={connectionMessage}
            onChange={onRuntimeChange}
            onCheckConnection={onCheckConnection}
            onSave={onSaveRuntime}
            onReset={onResetRuntime}
          />
        )}

        <nav className="workspace-tabs" role="tablist" aria-label="QA workspace">
          {workspaces.map((workspace, index) => (
            <button
              key={workspace.id}
              id={`workspace-tab-${workspace.id}`}
              type="button"
              role="tab"
              aria-selected={activeWorkspace === workspace.id}
              aria-controls={`workspace-panel-${workspace.id}`}
              tabIndex={activeWorkspace === workspace.id ? 0 : -1}
              onClick={() => setActiveWorkspace(workspace.id)}
              onKeyDown={(event) => handleWorkspaceKeyDown(event, index)}
            >
              <span className="workspace-status-dot" aria-hidden="true" />
              {workspace.label}
            </button>
          ))}
        </nav>

        <div
          id="workspace-panel-v1"
          role="tabpanel"
          aria-labelledby="workspace-tab-v1"
          hidden={activeWorkspace !== "v1"}
        >
          <V1Workspace
            createClient={createV1Client}
            onRunLockChange={onV1RunLockChange}
          />
        </div>
        <div
          id="workspace-panel-comparison"
          role="tabpanel"
          aria-labelledby="workspace-tab-comparison"
          hidden={activeWorkspace !== "comparison"}
        >
          <ComparisonWorkspace
            createClient={createComparisonClient}
            onRunLockChange={onComparisonRunLockChange}
          />
        </div>
      </main>

      <EvidenceDrawer
        open={evidenceOpen}
        calls={calls}
        onClose={() => setEvidenceOpen(false)}
        returnFocusRef={evidenceTriggerRef}
      />
    </div>
  );
}
