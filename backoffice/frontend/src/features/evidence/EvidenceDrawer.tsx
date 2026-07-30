import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject
} from "react";
import { X } from "lucide-react";
import type { ApiCallRecord } from "../../domain/apiCall";
import { JsonViewer, stringifyJson } from "./JsonViewer";

type EvidenceTab = "request" | "parsed" | "raw" | "error";

interface EvidenceDrawerProps {
  open: boolean;
  calls: ApiCallRecord[];
  onClose: () => void;
  returnFocusRef?: RefObject<HTMLButtonElement | null>;
}

const evidenceTabs: Array<{ id: EvidenceTab; label: string }> = [
  { id: "request", label: "요청" },
  { id: "parsed", label: "Parsed 응답" },
  { id: "raw", label: "Raw 응답" },
  { id: "error", label: "오류" }
];

export function EvidenceDrawer({
  open,
  calls,
  onClose,
  returnFocusRef
}: EvidenceDrawerProps) {
  const [selectedId, setSelectedId] = useState<string>();
  const [activeTab, setActiveTab] = useState<EvidenceTab>("request");
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);

  const selected =
    calls.find((call) => call.id === selectedId) ??
    calls[calls.length - 1];

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        returnFocusRef?.current?.focus();
      } else if (event.key === "Tab") {
        const focusable = Array.from(
          drawerRef.current?.querySelectorAll<HTMLElement>(
            'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
          ) ?? []
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open, returnFocusRef]);

  useEffect(() => {
    if (selected && !selectedId) setSelectedId(selected.id);
  }, [selected, selectedId]);

  const tabContent = useMemo(() => {
    if (!selected) return "";
    if (activeTab === "request") {
      return stringifyJson({
        headers: selected.requestHeaders,
        body: selected.request
      });
    }
    if (activeTab === "parsed") return stringifyJson(selected.parsed);
    if (activeTab === "raw") {
      return selected.rawText || "표시할 raw response가 없습니다.";
    }
    return selected.error || "기록된 오류가 없습니다.";
  }, [activeTab, selected]);

  if (!open) return null;

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number
  ) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? evidenceTabs.length - 1
          : (index + (event.key === "ArrowRight" ? 1 : -1) + evidenceTabs.length) %
            evidenceTabs.length;
    const nextTab = evidenceTabs[nextIndex];
    setActiveTab(nextTab.id);
    document.getElementById(`evidence-tab-${nextTab.id}`)?.focus();
  }

  return (
    <div
      className="drawer-backdrop"
      onMouseDown={() => {
        onClose();
        returnFocusRef?.current?.focus();
      }}
    >
      <aside
        ref={drawerRef}
        className="evidence-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          <div>
            <p className="eyebrow">API Evidence</p>
            <h2 id="evidence-title">Evidence Drawer</h2>
          </div>
          <button
            ref={closeButtonRef}
            className="icon-button"
            type="button"
            aria-label="Evidence Drawer 닫기"
            onClick={() => {
              onClose();
              returnFocusRef?.current?.focus();
            }}
          >
            <X aria-hidden="true" />
          </button>
        </header>

        {calls.length === 0 ? (
          <div className="drawer-empty">
            <p>아직 API 호출 기록이 없습니다.</p>
            <span>연결 확인을 실행하면 여기에 증적이 추가됩니다.</span>
          </div>
        ) : (
          <div className="evidence-layout">
            <ol className="call-timeline" aria-label="API 호출 목록">
              {calls.map((call, index) => (
                <li key={call.id}>
                  <button
                    type="button"
                    className={call.id === selected?.id ? "selected" : ""}
                    aria-current={call.id === selected?.id ? "true" : undefined}
                    onClick={() => setSelectedId(call.id)}
                  >
                    <span className="call-order">{index + 1}</span>
                    <strong>
                      {call.method} · {call.httpStatus ?? "HTTP —"}
                    </strong>
                    <span>{call.url}</span>
                    <small>
                      {call.metadata?.workflow
                        ? `${call.metadata.workflow}${call.metadata.step ? `/${call.metadata.step}` : ""}${call.metadata.version ? `/${call.metadata.version}` : ""} · `
                        : ""}
                      {call.transportStatus} · {call.judgment} · {call.elapsedMs}ms
                    </small>
                  </button>
                </li>
              ))}
            </ol>

            {selected && (
              <section className="call-detail" aria-label="선택한 API 호출">
                <dl className="call-meta">
                  <div>
                    <dt>Method</dt>
                    <dd>{selected.method}</dd>
                  </div>
                  <div>
                    <dt>HTTP</dt>
                    <dd>{selected.httpStatus ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Transport</dt>
                    <dd>{selected.transportStatus}</dd>
                  </div>
                  <div>
                    <dt>Judgment</dt>
                    <dd>{selected.judgment}</dd>
                  </div>
                  <div>
                    <dt>Elapsed</dt>
                    <dd>{selected.elapsedMs}ms</dd>
                  </div>
                  <div>
                    <dt>Workflow</dt>
                    <dd>{selected.metadata?.workflow ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Step / Version</dt>
                    <dd>
                      {selected.metadata?.step ?? "—"}
                      {selected.metadata?.version
                        ? ` / ${selected.metadata.version}`
                        : ""}
                    </dd>
                  </div>
                </dl>
                <p className="call-url">{selected.url}</p>

                <div className="inspector-tabs" role="tablist" aria-label="증적 상세">
                  {evidenceTabs.map((tab, index) => (
                    <button
                      key={tab.id}
                      id={`evidence-tab-${tab.id}`}
                      type="button"
                      role="tab"
                      aria-selected={activeTab === tab.id}
                      aria-controls="evidence-tab-panel"
                      tabIndex={activeTab === tab.id ? 0 : -1}
                      onClick={() => setActiveTab(tab.id)}
                      onKeyDown={(event) => handleTabKeyDown(event, index)}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div
                  id="evidence-tab-panel"
                  className="json-panel evidence-json-panel"
                  role="tabpanel"
                >
                  <JsonViewer
                    key={`${selected.id}-${activeTab}`}
                    value={tabContent}
                    label={
                      evidenceTabs.find((tab) => tab.id === activeTab)?.label
                    }
                  />
                </div>
              </section>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
