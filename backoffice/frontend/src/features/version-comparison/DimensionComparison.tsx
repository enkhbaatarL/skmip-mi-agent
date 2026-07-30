import type { ApiVersion } from "../../domain/apiTypes";
import {
  VERSION_ORDER,
  type VersionRunState
} from "./types";

interface DimensionComparisonProps {
  versions: Record<ApiVersion, VersionRunState>;
}

export function DimensionComparison({
  versions
}: DimensionComparisonProps) {
  return (
    <section aria-labelledby="dimensions-title">
      <h3 id="dimensions-title">Dimensions</h3>
      <p className="comparison-help">
        v2는 Event namespace, v3는 composite/multi-source, v4는 model lever와
        support 상태를 중심으로 표시합니다.
      </p>
      <div className="version-detail-grid">
        {VERSION_ORDER.map((version) => {
          const state = versions[version];
          const data =
            state.status === "success" ? state.response?.data ?? undefined : undefined;
          if (!data) {
            return (
              <article className="detail-column" key={version}>
                <h4>{version}</h4>
                <p className="empty-hint">
                  성공한 비교 데이터가 없습니다. Raw에서 원본을 확인하세요.
                </p>
              </article>
            );
          }
          const diagnostics = data.generationDiagnostics;
          return (
            <article className="detail-column" key={version}>
              <h4>
                {version} · {data.dimensionDefinitions.length}개
              </h4>
              <div className="dimension-list">
                {data.dimensionDefinitions.map((dimension) => {
                  const covered = diagnostics.coveredDimensions.includes(
                    dimension.dimensionId
                  );
                  const uncovered = diagnostics.uncoveredDimensions.includes(
                    dimension.dimensionId
                  );
                  const unsupported = diagnostics.unsupportedLeverDetails.filter(
                    (item) => dimension.leverRefs.includes(item.leverCode)
                  );
                  return (
                    <details
                      className={`dimension-item dimension-${version}`}
                      key={dimension.dimensionId}
                    >
                      <summary>
                        <code>{dimension.dimensionId}</code>
                        <span>{dimension.label}</span>
                      </summary>
                      <div className="dimension-body">
                        <p>{dimension.description}</p>
                        <dl className="compact-definition">
                          <div>
                            <dt>Type / kind</dt>
                            <dd>
                              {dimension.dimensionType ?? "—"} /{" "}
                              {dimension.valueKind ?? "—"}
                            </dd>
                          </div>
                          <div>
                            <dt>Source Events</dt>
                            <dd>{dimension.sourceEventIds.join(", ") || "—"}</dd>
                          </div>
                          <div>
                            <dt>Lever refs</dt>
                            <dd>{dimension.leverRefs.join(", ") || "—"}</dd>
                          </div>
                          <div>
                            <dt>Model support</dt>
                            <dd>{dimension.modelSupportStatus ?? "—"}</dd>
                          </div>
                          <div>
                            <dt>Coverage</dt>
                            <dd>
                              {covered ? "covered" : uncovered ? "uncovered" : "미지정"}
                            </dd>
                          </div>
                        </dl>
                        <div>
                          <strong>Values</strong>
                          <ul className="compact-list">
                            {dimension.values.map((value) => (
                              <li key={value.valueId}>
                                <code>{value.valueId}</code> · {value.label}
                                {value.globalPressureContribution
                                  ? ` · ${value.globalPressureContribution}`
                                  : ""}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <strong>Source lineage</strong>
                          {dimension.sourceRefs.length === 0 ? (
                            <p className="empty-hint">sourceRefs 없음</p>
                          ) : (
                            <ul className="lineage-list">
                              {dimension.sourceRefs.map((source, index) => (
                                <li
                                  key={`${source.eventId}-${source.dimKey}-${index}`}
                                >
                                  Event #{source.eventId} ·{" "}
                                  <code>{source.dimKey}</code> · {source.sourceType} ·{" "}
                                  {source.rationale}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                        {unsupported.length > 0 && (
                          <div className="callout warning compact-callout">
                            {unsupported.map((item) => (
                              <span key={`${item.leverCode}-${item.reasonCode}`}>
                                {item.leverCode}: {item.reasonCode}
                                {item.parameterName
                                  ? ` (${item.parameterName})`
                                  : ""}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </details>
                  );
                })}
              </div>
            </article>
          );
        })}
      </div>

      <details className="lineage-matrix">
        <summary>전체 source-lineage matrix</summary>
        <div className="table-scroll" tabIndex={0}>
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Dimension</th>
                <th>Event</th>
                <th>Source dimension</th>
                <th>Lineage type</th>
                <th>Assumption</th>
              </tr>
            </thead>
            <tbody>
              {VERSION_ORDER.flatMap((version) => {
                const data =
                  versions[version].status === "success"
                    ? versions[version].response?.data
                    : undefined;
                return (data?.dimensionDefinitions ?? []).flatMap((dimension) =>
                  dimension.sourceRefs.map((source, index) => (
                    <tr
                      key={`${version}-${dimension.dimensionId}-${source.eventId}-${index}`}
                    >
                      <td>{version}</td>
                      <td>{dimension.dimensionId}</td>
                      <td>{source.eventId}</td>
                      <td>{source.dimKey}</td>
                      <td>{source.sourceType}</td>
                      <td>{source.assumptionYn}</td>
                    </tr>
                  ))
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
