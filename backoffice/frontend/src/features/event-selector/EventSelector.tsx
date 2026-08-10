import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, CheckCircle2, Search, X } from "lucide-react";
import type { AgentClient } from "../../api/agentClient";
import { getEventDetail } from "../../api/v1Pipeline";
import type {
  EventDetail,
  EventListResponse,
  EventListRow
} from "../../domain/apiTypes";

export interface EventSelectorProps {
  mode: "single" | "multi";
  selectedEvents: EventDetail[];
  onChange: (events: EventDetail[]) => void;
  client: AgentClient;
  disabled?: boolean;
}

type SelectionMode = "direct" | "list";

interface EventFilters {
  keyword: string;
  sort: "latest" | "oldest";
  status: "" | "new" | "updated";
  eventTypeL1Id: string;
  eventTypeL2Id: string;
  recommendedOnly: boolean;
  page: number;
  pageSize: number;
}

const initialFilters: EventFilters = {
  keyword: "",
  sort: "latest",
  status: "",
  eventTypeL1Id: "",
  eventTypeL2Id: "",
  recommendedOnly: false,
  page: 1,
  pageSize: 20
};

function eventTitle(event: EventListRow): string {
  return event.title || event.eventTitle || `Event ${event.miEventId}`;
}

function eventTime(event: EventListRow): string {
  return event.occurredAt || event.eventTime || "—";
}

function buildListPath(filters: EventFilters): string {
  const query = new URLSearchParams({
    sort: filters.sort,
    page: String(filters.page),
    pageSize: String(filters.pageSize)
  });
  if (filters.keyword.trim()) query.set("keyword", filters.keyword.trim());
  if (filters.status) query.set("status", filters.status);
  if (filters.eventTypeL1Id.trim()) {
    query.set("eventTypeL1Id", filters.eventTypeL1Id.trim());
  }
  if (filters.eventTypeL2Id.trim()) {
    query.set("eventTypeL2Id", filters.eventTypeL2Id.trim());
  }
  if (filters.recommendedOnly) query.set("recommendedOnly", "true");
  return `/events?${query.toString()}`;
}

function marketImpactText(event: EventDetail): string | undefined {
  const templateImpact = event.scenarioTemplate?.lngPriceImpactExamples;
  if (typeof templateImpact === "string" && templateImpact.trim()) {
    return templateImpact.trim();
  }
  if (templateImpact != null) {
    try {
      return JSON.stringify(templateImpact);
    } catch {
      return String(templateImpact);
    }
  }
  const impactPattern = /\b(?:JKM|TTF|HH)\b|시장\s*영향|가격\s*영향/i;
  const matchingTags = event.tags.filter((tag) => impactPattern.test(tag));
  const values = [
    ...matchingTags,
    ...(impactPattern.test(event.detailAnalysis) ? [event.detailAnalysis] : [])
  ];
  return values.length ? values.join(" · ") : undefined;
}

export function EventSelector({
  mode,
  selectedEvents,
  onChange,
  client,
  disabled = false
}: EventSelectorProps) {
  const [selectionMode, setSelectionMode] = useState<SelectionMode>("list");
  const [directId, setDirectId] = useState("");
  const [draftFilters, setDraftFilters] =
    useState<EventFilters>(initialFilters);
  const [filters, setFilters] = useState<EventFilters>(initialFilters);
  const [list, setList] = useState<EventListResponse>();
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetailId, setLoadingDetailId] = useState<number>();
  const [error, setError] = useState("");
  const [inputError, setInputError] = useState("");
  const selectedIds = useMemo(
    () => new Set(selectedEvents.map((event) => event.miEventId)),
    [selectedEvents]
  );

  useEffect(() => {
    if (selectionMode !== "list") return;
    let active = true;
    setLoadingList(true);
    setError("");
    void client
      .request<EventListResponse>(buildListPath(filters), {
        method: "GET",
        evidence: { step: "event-list" }
      })
      .then((result) => {
        if (!active) return;
        if (result.ok && result.data) {
          setList(result.data);
        } else {
          setError(
            result.record.error ??
              "Event 목록을 불러오지 못했습니다. 기존 선택은 유지됩니다."
          );
        }
      })
      .finally(() => {
        if (active) setLoadingList(false);
      });
    return () => {
      active = false;
    };
  }, [client, filters, selectionMode]);

  async function selectEvent(row: EventListRow | number, toggle = false) {
    const miEventId = typeof row === "number" ? row : row.miEventId;
    if (disabled || loadingDetailId !== undefined) return;
    if (mode === "multi" && selectedIds.has(miEventId)) {
      if (toggle) {
        onChange(
          selectedEvents.filter((event) => event.miEventId !== miEventId)
        );
      } else {
        setError("이미 선택한 miEventId입니다. 선택 순서는 유지됩니다.");
      }
      return;
    }
    if (mode === "multi" && selectedEvents.length >= 5) {
      setError("Event는 최대 5건까지 선택할 수 있습니다.");
      return;
    }

    setLoadingDetailId(miEventId);
    setError("");
    const result = await getEventDetail(client, miEventId);
    setLoadingDetailId(undefined);
    if (result.status !== "success" || !result.data?.event) {
      setError(
        result.record.error ??
          "Event 상세를 불러오지 못했습니다. 기존 선택은 유지됩니다."
      );
      return;
    }
    const detail: EventDetail = {
      ...result.data.event,
      scenarioTemplate: result.data.scenarioTemplate,
      source: result.data.source
    };
    onChange(mode === "single" ? [detail] : [...selectedEvents, detail]);
  }

  function submitDirect(event: FormEvent) {
    event.preventDefault();
    const id = Number(directId);
    if (!Number.isSafeInteger(id) || id <= 0) {
      setInputError("miEventId는 양의 정수여야 합니다.");
      return;
    }
    setInputError("");
    void selectEvent(id);
  }

  function submitFilters(event: FormEvent) {
    event.preventDefault();
    setFilters({ ...draftFilters, page: 1 });
  }

  function movePage(page: number) {
    const next = { ...draftFilters, page };
    setDraftFilters(next);
    setFilters(next);
  }

  return (
    <section
      className="event-selector"
      aria-labelledby="event-selector-title"
      aria-busy={loadingList || loadingDetailId !== undefined}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Event Selector</p>
          <h2 id="event-selector-title">
            {mode === "single" ? "단일 Event 선택" : "Event 1~5건 선택"}
          </h2>
        </div>
        <span className="selection-count" aria-live="polite">
          {selectedEvents.length}건 선택
        </span>
      </div>

      <div className="segmented-control" aria-label="Event 선택 방법">
        <button
          type="button"
          aria-pressed={selectionMode === "direct"}
          disabled={disabled}
          onClick={() => setSelectionMode("direct")}
        >
          ID 직접 입력
        </button>
        <button
          type="button"
          aria-pressed={selectionMode === "list"}
          disabled={disabled}
          onClick={() => setSelectionMode("list")}
        >
          목록에서 선택
        </button>
      </div>

      {selectionMode === "direct" ? (
        <form className="direct-event-form" onSubmit={submitDirect}>
          <label className="field">
            miEventId
            <input
              inputMode="numeric"
              value={directId}
              disabled={disabled || loadingDetailId !== undefined}
              aria-invalid={Boolean(inputError)}
              aria-describedby={inputError ? "direct-event-error" : undefined}
              onChange={(event) => {
                setDirectId(event.currentTarget.value);
                setInputError("");
              }}
            />
          </label>
          <button
            className="button primary"
            type="submit"
            disabled={disabled || loadingDetailId !== undefined}
          >
            상세 조회 후 선택
          </button>
          {inputError && (
            <span className="field-error" id="direct-event-error">
              {inputError}
            </span>
          )}
        </form>
      ) : (
        <>
          <form className="event-filters" onSubmit={submitFilters}>
            <label className="field filter-keyword">
              Keyword
              <input
                value={draftFilters.keyword}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    keyword: event.currentTarget.value
                  }))
                }
              />
            </label>
            <label className="field">
              정렬
              <select
                value={draftFilters.sort}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    sort: event.currentTarget.value as EventFilters["sort"]
                  }))
                }
              >
                <option value="latest">최신순</option>
                <option value="oldest">오래된순</option>
              </select>
            </label>
            <label className="field">
              상태
              <select
                value={draftFilters.status}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    status: event.currentTarget.value as EventFilters["status"]
                  }))
                }
              >
                <option value="">전체</option>
                <option value="new">new</option>
                <option value="updated">updated</option>
              </select>
            </label>
            <label className="field">
              Event Type L1 ID
              <input
                inputMode="numeric"
                value={draftFilters.eventTypeL1Id}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    eventTypeL1Id: event.currentTarget.value
                  }))
                }
              />
            </label>
            <label className="field">
              Event Type L2 ID
              <input
                inputMode="numeric"
                value={draftFilters.eventTypeL2Id}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    eventTypeL2Id: event.currentTarget.value
                  }))
                }
              />
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={draftFilters.recommendedOnly}
                disabled={disabled}
                onChange={(event) =>
                  setDraftFilters((current) => ({
                    ...current,
                    recommendedOnly: event.currentTarget.checked
                  }))
                }
              />
              추천 항목만
            </label>
            <button className="button secondary" type="submit" disabled={disabled}>
              <Search aria-hidden="true" size={16} />
              조회
            </button>
          </form>

          {error && (
            <div className="callout error" role="alert">
              <AlertCircle aria-hidden="true" size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="table-scroll event-table-scroll" tabIndex={0}>
            <table className="event-table">
              <thead>
                <tr>
                  <th scope="col">선택</th>
                  <th scope="col">miEventId</th>
                  <th scope="col">제목</th>
                  <th scope="col">발생시각</th>
                  <th scope="col">Event Type L1</th>
                  <th scope="col">Event Type L2</th>
                  <th scope="col">추천상태</th>
                  <th scope="col">기존 Scenario Group</th>
                </tr>
              </thead>
              <tbody>
                {loadingList
                  ? Array.from({ length: 4 }, (_, index) => (
                      <tr key={`skeleton-${index}`} className="skeleton-row">
                        <td colSpan={8}>
                          <span aria-hidden="true" />
                          {index === 0 && (
                            <span className="sr-only">
                              Event 목록을 불러오고 있습니다.
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  : list?.rows.map((row) => {
                      const selected = selectedIds.has(row.miEventId);
                      const unavailable =
                        row.scenarioActionState.disabled ||
                        (mode === "multi" &&
                          !selected &&
                          selectedEvents.length >= 5);
                      return (
                        <tr key={row.miEventId}>
                          <td>
                            <input
                              type={mode === "single" ? "radio" : "checkbox"}
                              name={mode === "single" ? "selected-event" : undefined}
                              aria-label={`${row.miEventId} Event 선택`}
                              checked={selected}
                              disabled={
                                disabled ||
                                unavailable ||
                                loadingDetailId !== undefined
                              }
                              title={
                                row.scenarioActionState.reason ?? undefined
                              }
                              onChange={() => void selectEvent(row, true)}
                            />
                          </td>
                          <td>{row.miEventId}</td>
                          <td className="event-title-cell">{eventTitle(row)}</td>
                          <td>{eventTime(row)}</td>
                          <td>{row.eventTypeL1?.label || "—"}</td>
                          <td>{row.eventTypeL2?.label || "—"}</td>
                          <td>
                            {row.scenarioSuggestYn === "Y"
                              ? "추천"
                              : "추천 아님"}
                            {row.scenarioSuggestReason && (
                              <small>{row.scenarioSuggestReason}</small>
                            )}
                          </td>
                          <td>
                            {row.relatedScenarioGroup
                              ? `#${row.relatedScenarioGroup.scenarioGroupId} · ${row.relatedScenarioGroup.status}/${row.relatedScenarioGroup.stage}`
                              : "없음"}
                          </td>
                        </tr>
                      );
                    })}
                {!loadingList && list?.rows.length === 0 && (
                  <tr>
                    <td colSpan={8} className="table-empty">
                      조건에 맞는 Event가 없습니다. 현재 filter는 유지됩니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {list && (
            <nav className="pagination" aria-label="Event 목록 페이지">
              <button
                className="button quiet compact"
                type="button"
                disabled={
                  disabled || loadingList || !list.pagination.hasPrevious
                }
                onClick={() => movePage(list.pagination.page - 1)}
              >
                이전
              </button>
              <span>
                {list.pagination.page} 페이지 · 총 {list.pagination.total}건
              </span>
              <button
                className="button quiet compact"
                type="button"
                disabled={disabled || loadingList || !list.pagination.hasNext}
                onClick={() => movePage(list.pagination.page + 1)}
              >
                다음
              </button>
            </nav>
          )}
        </>
      )}

      {selectionMode === "direct" && error && (
        <div className="callout error" role="alert">
          <AlertCircle aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="selected-events" aria-label="선택한 Event">
        {selectedEvents.length === 0 ? (
          <p className="empty-hint">Create에 사용할 Event를 선택하세요.</p>
        ) : (
          selectedEvents.map((event, index) => {
            const impact = marketImpactText(event);
            return (
              <article className="selected-event-card" key={event.miEventId}>
                <div className="selected-event-heading">
                  <div>
                    {mode === "multi" && (
                      <span className="order-badge">{index + 1}</span>
                    )}
                    <strong>
                      #{event.miEventId} · {eventTitle(event)}
                    </strong>
                  </div>
                  {!disabled && mode === "multi" && (
                    <button
                      className="icon-button"
                      type="button"
                      aria-label={`${event.miEventId} Event 선택 해제`}
                      onClick={() =>
                        onChange(
                          selectedEvents.filter(
                            (item) => item.miEventId !== event.miEventId
                          )
                        )
                      }
                    >
                      <X aria-hidden="true" size={17} />
                    </button>
                  )}
                </div>
                <p>{event.oneLineSummary || "한 줄 요약 없음"}</p>
                <dl className="event-meta">
                  <div>
                    <dt>발생시각</dt>
                    <dd>{eventTime(event)}</dd>
                  </div>
                  <div>
                    <dt>Event Type</dt>
                    <dd>
                      {event.eventTypeL1?.label || "—"} /{" "}
                      {event.eventTypeL2?.label || "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>Scenario 추천</dt>
                    <dd>
                      {event.scenarioSuggestYn === "Y" ? "추천" : "추천 아님"}
                      {event.scenarioSuggestReason
                        ? ` · ${event.scenarioSuggestReason}`
                        : ""}
                    </dd>
                  </div>
                  <div>
                    <dt>기존 Group</dt>
                    <dd>
                      {event.relatedScenarioGroup
                        ? `#${event.relatedScenarioGroup.scenarioGroupId} · ${event.relatedScenarioGroup.status}/${event.relatedScenarioGroup.stage}`
                        : "없음"}
                    </dd>
                  </div>
                </dl>
                {event.keyBullets?.length > 0 && (
                  <ul>
                    {event.keyBullets.map((bullet, bulletIndex) => (
                      <li key={`${event.miEventId}-bullet-${bulletIndex}`}>
                        {bullet}
                      </li>
                    ))}
                  </ul>
                )}
                {impact && (
                  <section className="market-impact-slot">
                    <h3>시장 영향</h3>
                    <p>{impact}</p>
                  </section>
                )}
                <span className="selected-marker">
                  <CheckCircle2 aria-hidden="true" size={16} /> 선택됨
                </span>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
